# ArXivCat Technical Memo

This document is for future maintainers.

It is intentionally more detailed than the README and focuses on how the project is structured, how the current packaging works, and what conventions have emerged so far.

## 1. Project purpose

ArXivCat is a focused utility for extracting readable paper text from arXiv LaTeX source packages.

The core workflow is:

1. parse an arXiv ID from user input
2. download the source tarball
3. unpack the source into a cache directory
4. locate the main TeX file
5. recursively expand `\input` / `\include`
6. split output into `body.tex` and `appendix.tex`
7. preview and lightly edit the result in the GUI

A lightweight Gemini chat panel was later added as reading assistance, not as a full retrieval or agent system.

## 2. Current top-level files

- `main.py`: GUI entry point
- `cli.py`: command-line entry point
- `arxivcat/core.py`: download and extraction logic
- `arxivcat/presenter.py`: UI-agnostic application logic
- `arxivcat/ui/tkinter_ui.py`: current GUI implementation
- `arxivcat/ui/base.py`: UI protocol
- `build.ps1`: Windows packaging script
- `pyi_rth_tk_env.py`: runtime hook for packaged Tk/Tcl environment setup

## 3. Architecture summary

### 3.1 Presenter pattern

The project currently uses a simple presenter-style separation.

- `Presenter` owns application logic and workflow state.
- `TkApp` owns widgets and UI rendering.
- `UIProtocol` defines the interface between them.

The goal here is not heavy abstraction. It is just enough separation so extraction logic is not deeply mixed into Tk widget code.

### 3.2 Extraction logic

Most of the paper-processing logic lives in `arxivcat/core.py`.

Important responsibilities include:

- parsing arXiv IDs from different input forms
- downloading arXiv source packages
- handling partially broken cache states
- finding the main TeX file
- recursively expanding `\input` and `\include`
- heuristically splitting body vs appendix

This logic is heuristic by design. It is meant to be practical on common arXiv papers, not mathematically complete for all LaTeX projects.

### 3.3 GUI logic

The current GUI is Tkinter-based.

Notable UI features:

- arXiv input field
- run button
- body / appendix switcher
- preview panel
- copy / overwrite / open folder / strip comments actions
- optional log panel
- right-side Gemini chat panel

The chat panel currently keeps short-lived in-memory history only.

## 4. Chat implementation notes

The chat panel is intentionally lightweight.

Current behavior:

- model: `gemini-3.1-flash-lite-preview`
- uses `GEMINI_API_KEY`
- sends current preview text as context
- includes recent short chat history
- `Reset` clears that in-memory history

Important limitation:

- this is not full-paper retrieval
- it is closer to “chat over current preview text”
- long papers may be truncated before sending to the model

So if someone wants better paper QA in the future, the likely next step is chunking or retrieval, not simply making the prompt longer forever.

## 5. Build and packaging notes

### 5.1 Why packaging needed extra care

Tkinter packaging on Windows can fail even when source execution works.

The specific issue seen in this project was a Tcl/Tk version mismatch during PyInstaller output, producing runtime errors like:

- missing `init.tcl`
- Tcl version conflicts such as `8.6.12` vs `8.6.15`

This happened because a build could accidentally mix:

- the wrong Python environment
- stale PyInstaller cache / spec files
- mismatched Tcl/Tk resources

### 5.2 Current packaging approach

`build.ps1` now does the following:

- explicitly uses `D:\anaconda3\envs\arxivcat\python.exe`
- removes previous `build/`, `dist/`, and generated `.spec`
- runs a clean PyInstaller build
- explicitly bundles:
  - `Library/lib/tcl8.6`
  - `Library/lib/tk8.6`
  - `Library/bin/tcl86t.dll`
  - `Library/bin/tk86t.dll`
- uses `pyi_rth_tk_env.py` to set:
  - `TCL_LIBRARY`
  - `TK_LIBRARY`
  at runtime inside the packaged app

This setup exists for a reason. Future maintainers should be careful before “simplifying” it.

### 5.3 Packaging assumptions

The current packaging script assumes:

- Windows
- conda environment name and location matching the existing setup
- PyInstaller-based one-file build

If the environment path changes, `build.ps1` should be updated accordingly.

## 6. README policy

The README should stay practical.

The project style so far suggests:

- do not oversell the tool
- explain what it does and what it does not do
- keep examples short but real
- include the screenshot with a relative path so GitHub rendering works

The screenshot should remain referenced like this:

```md
![ArXivCat screenshot](assets/screenshot.png)
```

Using a local absolute path would break rendering on GitHub.

## 7. Commit comment style in this repo

Recent commit history suggests a simple, low-ceremony style.

Examples include:

- `some updates`
- `modify readme`
- `0.3.0`
- `fix tkinter build`
- `0.2.1, switched to tkinter and fixed extraction`

Very short summary of the style:

- keep it concise
- usually lowercase
- say what changed plainly
- version bumps can be just the version number
- no need for conventional commit prefixes unless the owner explicitly wants that later

A practical rule of thumb for this repo:

- feature or doc tweak: a short natural phrase
- version release: just the version number is acceptable
- bug fix: a short direct description

## 8. Things to watch out for

### 8.1 Cache handling

The cache logic tries to be resilient, including repair / fallback behavior when a cache directory is unreadable or locked.

That is useful, but it also means file and directory behavior on Windows matters a lot.

### 8.2 Heuristic extraction

The body/appendix split is heuristic. Before changing it, test against multiple real papers.

### 8.3 Chat scope creep

The chat panel is easy to bloat. It should remain simple unless there is a strong reason to add more complexity.

In particular, avoid adding a full retrieval pipeline unless the use case is clear.

## 9. Suggested maintenance habits

- test both GUI and CLI after touching extraction logic
- test packaged Windows builds after touching Tk or build config
- keep release artifacts aligned with the version shown in the GUI
- avoid mixing unrelated changes into the same commit
- when in doubt, prefer direct and readable code over abstraction

## 10. Open questions for future work

Reasonable future improvements could include:

- better context selection for chat
- easier configuration of the Gemini model
- more robust TeX main-file detection
- improved extraction heuristics for unusual paper layouts
- a small smoke test for packaged app startup

But none of these are mandatory right now. The current project is intentionally simple and that simplicity is worth preserving.
