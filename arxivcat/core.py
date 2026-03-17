import os
import requests
import tarfile
import re
import shutil
import argparse
from pathlib import Path


# ── Utilities ─────────────────────────────────────────────────

def extract_arxiv_id(input_str):
    match = re.search(r'(\d+\.\d+)', input_str)
    return match.group(1) if match else None


def sanitize_filename(name):
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    name = re.sub(r'[\s_]+', '_', name)
    return name.strip('_')[:80]


def fetch_title_from_arxiv(arxiv_id):
    try:
        resp = requests.get(f"https://arxiv.org/abs/{arxiv_id}", timeout=15)
        resp.raise_for_status()
        m = re.search(r'<meta property="og:title" content="(.+?)"', resp.text)
        if m:
            return m.group(1).strip()
    except Exception as e:
        print(f"[WARN] Failed to fetch title: {e}")
    return None


# ── Download & Extract ────────────────────────────────────────

def download_source(arxiv_id, downloads_dir):
    """Download and unpack arXiv source. Returns (paper_dir, folder_name)."""
    print(f"[INFO] Fetching title for {arxiv_id}...")
    title = fetch_title_from_arxiv(arxiv_id) or "unknown"
    print(f"[INFO] Title: {title}")

    folder_name = f"{arxiv_id.replace('.', '_')}_{sanitize_filename(title)}"
    paper_dir = downloads_dir / folder_name

    if paper_dir.exists() and any(paper_dir.glob("*.tex")):
        print(f"[INFO] Already cached, skipping download.")
        return paper_dir, folder_name

    print("[INFO] Downloading source...")
    try:
        resp = requests.get(
            f"https://arxiv.org/src/{arxiv_id}",
            timeout=120,
            stream=True,
        )
        resp.raise_for_status()
    except Exception as e:
        print(f"[ERROR] Download failed: {e}")
        return None, None

    total = int(resp.headers.get("content-length", 0))
    temp_tar = downloads_dir / f"{arxiv_id}.tar.gz"
    downloaded = 0
    chunk_size = 8192
    last_pct = -1

    with open(temp_tar, "wb") as f:
        for chunk in resp.iter_content(chunk_size=chunk_size):
            if chunk:
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = int(downloaded / total * 100)
                    if pct != last_pct and pct % 10 == 0:
                        print(f"[INFO] Downloading... {pct}% ({downloaded // 1024} KB / {total // 1024} KB)")
                        last_pct = pct
                else:
                    kb = downloaded // 1024
                    if kb % 200 == 0 and kb != 0:
                        print(f"[INFO] Downloading... {kb} KB received")

    print(f"[OK] Download complete ({downloaded // 1024} KB)")

    print("[INFO] Extracting archive...")
    temp_dir = downloads_dir / arxiv_id
    temp_dir.mkdir(exist_ok=True)
    try:
        with tarfile.open(temp_tar, 'r:gz') as tar:
            members = tar.getmembers()
            for i, member in enumerate(members):
                tar.extract(member, temp_dir)
                if len(members) > 0 and (i + 1) % max(1, len(members) // 5) == 0:
                    pct = int((i + 1) / len(members) * 100)
                    print(f"[INFO] Extracting... {pct}% ({i + 1}/{len(members)} files)")
    except Exception as e:
        print(f"[ERROR] Extraction failed: {e}")
        return None, None

    paper_dir.mkdir(parents=True, exist_ok=True)
    for item in temp_dir.iterdir():
        dest = paper_dir / item.name
        if dest.exists():
            shutil.rmtree(dest) if dest.is_dir() else dest.unlink()
        shutil.move(str(item), str(dest))

    temp_dir.rmdir()
    temp_tar.unlink()
    print(f"[OK] Source saved to: {paper_dir}")
    return paper_dir, folder_name


# ── TeX Extraction ────────────────────────────────────────────

def expand_inputs(tex_content, base_dir):
    """Recursively expand all \\input{} and \\include{} commands."""
    def replace_input(match):
        filename = match.group(1).strip()
        if not filename.endswith('.tex'):
            filename += '.tex'
        filepath = base_dir / filename
        if filepath.exists():
            sub = filepath.read_text(encoding='utf-8', errors='ignore')
            return expand_inputs(sub, filepath.parent)
        return match.group(0)
    return re.sub(r'\\(?:input|include)\s*\{([^}]+)\}', replace_input, tex_content)


def find_main_tex(paper_dir):
    """Find the main .tex file (contains \\documentclass)."""
    if (paper_dir / "main.tex").exists():
        return paper_dir / "main.tex"
    for tex_file in paper_dir.glob("*.tex"):
        try:
            content = tex_file.read_text(encoding='utf-8', errors='ignore')
            if r'\documentclass' in content:
                return tex_file
        except Exception:
            continue
    return None


def extract_body_and_appendix(tex_content):
    """Extract body and appendix. Returns (body, appendix, error)."""
    abstract_match = re.search(r'\\begin\{abstract\}', tex_content)
    first_section_match = re.search(r'\\section\s*[\*]?\s*\{', tex_content)

    if abstract_match and first_section_match:
        start = min(abstract_match.start(), first_section_match.start())
    elif abstract_match:
        start = abstract_match.start()
    elif first_section_match:
        start = first_section_match.start()
    else:
        return None, None, "Could not find abstract or first section"

    conclusion_matches = list(re.finditer(
        r'\\section\*?\s*\{[^}]*(?:[Cc]onclusion|[Ss]ummary)[^}]*\}', tex_content
    ))

    appendix_sep = re.search(
        r'\\appendix(?:\s|$)|\\begin\{appendix\}',
        tex_content
    )
    bibliography_sep = re.search(
        r'\\bibliography(?:style)?\s*\{',
        tex_content
    )

    candidates = []
    if appendix_sep and appendix_sep.start() > start:
        candidates.append(appendix_sep.start())
    if bibliography_sep and bibliography_sep.start() > start:
        candidates.append(bibliography_sep.start())

    if candidates:
        body_end = min(candidates)
    elif conclusion_matches:
        conclusion_start = conclusion_matches[-1].start()
        after = tex_content[conclusion_start + 1:]
        next_sec = re.search(r'\\(?:section|chapter)\s*[\*]?\s*\{', after)
        if next_sec:
            body_end = conclusion_start + 1 + next_sec.start()
        else:
            end_doc = re.search(r'\\end\{document\}', tex_content[conclusion_start:])
            body_end = conclusion_start + (end_doc.start() if end_doc else len(tex_content[conclusion_start:]))
    else:
        end_doc = re.search(r'\\end\{document\}', tex_content)
        body_end = end_doc.start() if end_doc else len(tex_content)

    body = tex_content[start:body_end].strip()

    after_body = tex_content[body_end:]
    end_doc = re.search(r'\\end\{document\}', after_body)
    app_end = end_doc.start() if end_doc else len(after_body)
    appendix_raw = after_body[:app_end].strip()

    appendix_cleaned = re.sub(r'\\bibliography(?:style)?\s*\{[^}]*\}', '', appendix_raw).strip()
    appendix_cleaned = re.sub(r'\\clearpage', '', appendix_cleaned).strip()
    appendix = appendix_cleaned if len(appendix_cleaned) > 50 else None

    return body, appendix, None


def extract_body_from_dir(paper_dir, output_dir, folder_name):
    """Extract body and appendix from paper directory."""
    main_tex = find_main_tex(paper_dir)
    if not main_tex:
        print("[ERROR] Could not find main .tex file")
        return None
    print(f"[INFO] Main file: {main_tex.name}")

    content = main_tex.read_text(encoding='utf-8', errors='ignore')
    print("[INFO] Expanding \\input references...")
    expanded = expand_inputs(content, paper_dir)

    print("[INFO] Parsing body (abstract → conclusion)...")
    body, appendix, err = extract_body_and_appendix(expanded)
    if err:
        print(f"[ERROR] {err}")
        return None

    out_dir = output_dir / folder_name
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / "body.tex"
    out_path.write_text(body, encoding='utf-8')
    print(f"[OK] body.tex saved ({len(body)} chars, {body.count(chr(10))} lines)")

    if appendix:
        app_path = out_dir / "appendix.tex"
        app_path.write_text(appendix, encoding='utf-8')
        print(f"[OK] appendix.tex saved ({len(appendix)} chars, {appendix.count(chr(10))} lines)")
    else:
        print("[INFO] No appendix detected")

    return out_path


# ── CLI Entry ─────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="ArxivCat: download and extract arXiv paper source")
    parser.add_argument("--url", required=True,
                        help="arXiv ID or URL, e.g. 2511.16655 or https://arxiv.org/abs/2511.16655")
    args = parser.parse_args()

    arxiv_id = extract_arxiv_id(args.url)
    if not arxiv_id:
        print("[ERROR] Could not parse arXiv ID")
        return

    print(f"[INFO] Processing paper: {arxiv_id}")

    base = Path(os.environ.get("APPDATA", Path.home())) / "ArxivCat"
    downloads_dir = base / "downloads"
    outputs_dir = base / "outputs"
    downloads_dir.mkdir(parents=True, exist_ok=True)
    outputs_dir.mkdir(parents=True, exist_ok=True)

    paper_dir, folder_name = download_source(arxiv_id, downloads_dir)
    if not paper_dir:
        return

    extract_body_from_dir(paper_dir, outputs_dir, folder_name)


if __name__ == "__main__":
    main()
