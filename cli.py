"""CLI entry point."""

import argparse
import os
from pathlib import Path

from arxivcat.core import extract_arxiv_id, download_source, extract_body_from_dir


def main():
    parser = argparse.ArgumentParser(description="ArxivCat: download and extract arXiv paper source")
    parser.add_argument(
        "--url",
        required=True,
        help="arXiv ID or URL, e.g. 2511.16655 or https://arxiv.org/abs/2511.16655",
    )
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
