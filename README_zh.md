# ArXivCat

[English README](README.md)

ArXivCat 是一个小型桌面工具，用来下载 arXiv 论文源码包，展开 LaTeX 里的 `\input` / `\include`，并导出相对干净的 `body.tex` 和 `appendix.tex`。

它面向一个很实际的工作流：粘贴 arXiv 链接或编号，查看提取结果，做一点轻量编辑，并且在需要时用右侧 Gemini chat 对当前加载的论文内容做简单问答。

![ArXivCat 截图](assets/screenshot.png)

## 这个项目能做什么

- 支持从 arXiv 页面链接、PDF 链接或纯 arXiv ID 下载源码包
- 自动解压并缓存源码
- 递归展开 LaTeX `\input` 和 `\include`
- 自动寻找主 TeX 文件，并导出：
  - `body.tex`
  - 如果存在则导出 `appendix.tex`
- 提供 Tkinter GUI，用于预览和轻量编辑提取结果
- 右侧带一个极简 Gemini chat，并支持 reset 清空短期记忆

## 这个项目不打算做什么

ArXivCat 的目标比较收敛。

- 它不是一个完整的 LaTeX 编译器。
- 它不保证对所有论文源码结构都能完美解析。
- 右侧 chat 更偏轻量阅读辅助，不是完整的检索增强问答系统。

## 安装

### Python 依赖

```bash
pip install -r requirements.txt
```

如果要使用右侧 chat，需要在环境变量里设置 `GEMINI_API_KEY`。

### 从源码运行

GUI：

```bash
python main.py
```

CLI：

```bash
python cli.py --url 2601.11514
python cli.py --url https://arxiv.org/abs/2601.11514
python cli.py --url https://arxiv.org/pdf/2601.11514
```

## GUI 使用流程

1. 粘贴 arXiv 链接或 ID
2. 点击 `Run`
3. 查看提取后的 `body` 或 `appendix`
4. 可选使用：
   - `Copy`
   - `Overwrite`
   - `Open Folder`
   - `Strip Comments`
5. 如果需要，可以用右侧 chat 对当前内容做简单解释或总结

## Chat 面板说明

当前 chat 使用 `gemini-3.1-flash-lite-preview`。

目前的行为：

- 会把当前预览区文本作为上下文发送
- 会保留一个短期的内存对话历史
- 点击 `Reset` 会清空当前 chat 记忆
- 最适合在左侧已经加载论文内容之后使用

## 输出目录

- 缓存：`%APPDATA%/ArxivCat/downloads/`
- 结果：`%APPDATA%/ArxivCat/outputs/`

如果缓存目录损坏或不可读，ArXivCat 会自动重下，或者写到 `*_freshN` 目录。

## 打包

Windows 打包目前使用 `build.ps1`，底层是 PyInstaller，默认依赖 `arxivcat` 这个 conda 环境。

## 给后续维护者

如果你是来继续维护这个项目的，建议先读 `tech_memo.md`。
