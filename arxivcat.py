import requests
import tarfile
import re
import shutil
import argparse
from pathlib import Path


# ── 工具函数 ──────────────────────────────────────────────────

def extract_arxiv_id(input_str):
    """从链接或ID提取arxiv ID"""
    match = re.search(r'(\d+\.\d+)', input_str)
    return match.group(1) if match else None


def sanitize_filename(name):
    """清理文件名中的非法字符"""
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    name = re.sub(r'[\s_]+', '_', name)
    return name.strip('_')[:80]


def fetch_title_from_arxiv(arxiv_id):
    """从arXiv网页抓取论文标题（og:title meta标签）"""
    try:
        resp = requests.get(f"https://arxiv.org/abs/{arxiv_id}", timeout=15)
        resp.raise_for_status()
        m = re.search(r'<meta property="og:title" content="(.+?)"', resp.text)
        if m:
            return m.group(1).strip()
    except Exception as e:
        print(f"[WARN] 获取标题失败: {e}")
    return None


# ── 下载 & 解压 ───────────────────────────────────────────────

def download_source(arxiv_id, downloads_dir):
    """下载并解压arxiv源码，返回解压后的文件夹路径"""
    title = fetch_title_from_arxiv(arxiv_id) or "unknown"
    print(f"[INFO] 标题: {title}")

    folder_name = f"{arxiv_id.replace('.', '_')}_{sanitize_filename(title)}"
    paper_dir = downloads_dir / folder_name

    if paper_dir.exists() and (paper_dir / "main.tex").exists():
        print(f"[INFO] 已存在，跳过下载: {paper_dir}")
        return paper_dir, folder_name

    print("[INFO] 下载中...")
    try:
        resp = requests.get(f"https://arxiv.org/src/{arxiv_id}", timeout=60)
        resp.raise_for_status()
    except Exception as e:
        print(f"[ERROR] 下载失败: {e}")
        return None, None

    temp_tar = downloads_dir / f"{arxiv_id}.tar.gz"
    temp_tar.write_bytes(resp.content)
    print("[OK] 下载完成")

    print("[INFO] 解压中...")
    temp_dir = downloads_dir / arxiv_id
    temp_dir.mkdir(exist_ok=True)
    try:
        with tarfile.open(temp_tar, 'r:gz') as tar:
            tar.extractall(temp_dir)
    except Exception as e:
        print(f"[ERROR] 解压失败: {e}")
        return None, None

    paper_dir.mkdir(parents=True, exist_ok=True)
    for item in temp_dir.iterdir():
        dest = paper_dir / item.name
        if dest.exists():
            shutil.rmtree(dest) if dest.is_dir() else dest.unlink()
        shutil.move(str(item), str(dest))

    temp_dir.rmdir()
    temp_tar.unlink()
    print(f"[OK] 源码保存到: {paper_dir}/")
    return paper_dir, folder_name


# ── tex 提取 ──────────────────────────────────────────────────

def expand_inputs(tex_content, base_dir):
    """递归展开所有 \\input{} 和 \\include{} 命令"""
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
    """找到论文主文件（含 \\documentclass 的 tex 文件）"""
    # 优先找 main.tex
    if (paper_dir / "main.tex").exists():
        return paper_dir / "main.tex"
    # 否则找含 \documentclass 的 tex 文件
    for tex_file in paper_dir.glob("*.tex"):
        try:
            content = tex_file.read_text(encoding='utf-8', errors='ignore')
            if r'\documentclass' in content:
                return tex_file
        except Exception:
            continue
    return None


def extract_body_and_appendix(tex_content):
    """提取正文和附录，返回 (body, appendix, err)"""
    # ── 确定正文起始点 ──
    abstract_match = re.search(r'\\begin\{abstract\}', tex_content)
    first_section_match = re.search(r'\\section\s*[\*]?\s*\{', tex_content)

    if abstract_match and first_section_match:
        start = min(abstract_match.start(), first_section_match.start())
    elif abstract_match:
        start = abstract_match.start()
    elif first_section_match:
        start = first_section_match.start()
    else:
        return None, None, "找不到 abstract 或 section"

    # ── 确定正文结束点：遇到 \appendix / \bibliography / \begin{appendix} 截断 ──
    # 先找 conclusion（用于在 conclusion 之后寻找截断点）
    conclusion_matches = list(re.finditer(
        r'\\section\*?\s*\{[^}]*(?:[Cc]onclusion|[Ss]ummary)[^}]*\}', tex_content
    ))

    # 搜索附录/参考文献分隔符
    appendix_sep = re.search(
        r'\\appendix(?:\s|$)|\\begin\{appendix\}',
        tex_content
    )
    bibliography_sep = re.search(
        r'\\bibliography(?:style)?\s*\{',
        tex_content
    )

    # 收集候选截断点（必须在 start 之后）
    candidates = []
    if appendix_sep and appendix_sep.start() > start:
        candidates.append(appendix_sep.start())
    if bibliography_sep and bibliography_sep.start() > start:
        candidates.append(bibliography_sep.start())

    if candidates:
        body_end = min(candidates)
    elif conclusion_matches:
        # 没有明确分隔符，就找 conclusion 后的下一个顶层 section
        conclusion_start = conclusion_matches[-1].start()
        after = tex_content[conclusion_start + 1:]  # +1 避免匹配到自身
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

    # ── 提取附录（body_end 之后到 \end{document}）──
    after_body = tex_content[body_end:]
    end_doc = re.search(r'\\end\{document\}', after_body)
    app_end = end_doc.start() if end_doc else len(after_body)
    appendix_raw = after_body[:app_end].strip()

    # 过滤掉纯参考文献行，剩余有实质内容才保留
    appendix_cleaned = re.sub(r'\\bibliography(?:style)?\s*\{[^}]*\}', '', appendix_raw).strip()
    appendix_cleaned = re.sub(r'\\clearpage', '', appendix_cleaned).strip()
    appendix = appendix_cleaned if len(appendix_cleaned) > 50 else None

    return body, appendix, None


def extract_body_from_dir(paper_dir, output_dir, folder_name):
    """从论文文件夹提取正文，输出到 outputs/ 对应子文件夹"""
    main_tex = find_main_tex(paper_dir)
    if not main_tex:
        print(f"[ERROR] 找不到主 tex 文件")
        return None
    print(f"[INFO] 主文件: {main_tex.name}")

    content = main_tex.read_text(encoding='utf-8', errors='ignore')
    print("[INFO] 展开 \\input 引用...")
    expanded = expand_inputs(content, paper_dir)

    print("[INFO] 提取正文 (abstract -> conclusion)...")
    body, appendix, err = extract_body_and_appendix(expanded)
    if err:
        print(f"[ERROR] {err}")
        return None

    out_dir = output_dir / folder_name
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / "body.tex"
    out_path.write_text(body, encoding='utf-8')
    print(f"[OK] body.tex 保存到: {out_path}")
    print(f"[INFO] 字符数: {len(body)}，行数: {body.count(chr(10))}")

    if appendix:
        app_path = out_dir / "appendix.tex"
        app_path.write_text(appendix, encoding='utf-8')
        print(f"[OK] appendix.tex 保存到: {app_path}")
        print(f"[INFO] 附录字符数: {len(appendix)}，行数: {appendix.count(chr(10))}")
    else:
        print("[INFO] 未检测到附录")

    return out_path


# ── 主入口 ────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="ArxivCat: 下载arxiv论文源码并提取正文")
    parser.add_argument("--url", required=True,
                        help="arXiv链接或ID，如 2511.16655 / https://arxiv.org/abs/2511.16655")
    args = parser.parse_args()

    arxiv_id = extract_arxiv_id(args.url)
    if not arxiv_id:
        print("[ERROR] 无法识别arXiv ID")
        return

    print(f"[INFO] 处理论文: {arxiv_id}")

    base = Path(__file__).parent
    downloads_dir = base / "downloads"
    outputs_dir = base / "outputs"
    downloads_dir.mkdir(exist_ok=True)
    outputs_dir.mkdir(exist_ok=True)

    # 1. 下载 & 解压
    paper_dir, folder_name = download_source(arxiv_id, downloads_dir)
    if not paper_dir:
        return

    # 2. 提取正文
    extract_body_from_dir(paper_dir, outputs_dir, folder_name)


if __name__ == "__main__":
    main()
