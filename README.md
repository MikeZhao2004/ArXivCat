# ArxivCat

Downloads an arXiv paper's LaTeX source and extracts the main text.

## What it does

1. Fetches the paper title from the arXiv page
2. Downloads and unpacks the `.tar.gz` source from `arxiv.org/src/{id}`
3. Recursively expands `\input{}` references
4. Splits content into `body.tex` (abstract → conclusion) and `appendix.tex` (if present)
5. Saves to `outputs/{id}_{title}/`

Source files are cached under `downloads/{id}_{title}/` and skipped on re-run.

## Usage

**CLI**
```bash
python arxivcat.py --url 2511.16655
python arxivcat.py --url https://arxiv.org/abs/2511.16655
```

**GUI**
```bash
python gui.py
```

Requires the `flet` environment: `conda activate flet`

## Output

```
downloads/
  2511_16655_{title}/       # raw source (cached)

outputs/
  2511_16655_{title}/
    body.tex
    appendix.tex            # if present
```

## Requirements

Python 3.8+

```bash
pip install requests flet
```

## Notes

- Not all papers have LaTeX source available on arXiv
- Multi-file projects with non-standard structures may not parse correctly
- Appendix extraction requires an explicit `\appendix` command in the source
