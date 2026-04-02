# ArXivCat

ArXivCat v0.3.0

下载 arXiv 的 LaTeX source，展开 `\input` / `\include`，导出 `body.tex` 和 `appendix.tex`。

现在 GUI 右侧带一个极简 Gemini chat，可基于当前预览内容做简单问答，并支持 reset 清空对话记忆。

## 用法

GUI:

```bash
python main.py
```

CLI:

```bash
python cli.py --url 2601.11514
python cli.py --url https://arxiv.org/abs/2601.11514
python cli.py --url https://arxiv.org/pdf/2601.11514
```

## 输出

- 缓存：`%APPDATA%/ArxivCat/downloads/`
- 结果：`%APPDATA%/ArxivCat/outputs/`

缓存坏了会自动重下；如果旧目录被系统锁住，会写到 `*_freshN` 目录。

## 依赖

```bash
pip install -r requirements.txt
```

如果要使用右侧 chat，还需要设置环境变量 `GEMINI_API_KEY`。

