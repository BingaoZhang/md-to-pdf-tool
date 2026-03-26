# md-to-pdf-tool

一个在 Windows 下使用的 Markdown 转 PDF 小工具，支持：

- 命令行版（`md_to_pdf.py` / `md_to_pdf.exe`）
- 图形界面版（`md_to_pdf_gui.py` / `md_to_pdf_gui.exe`）

## 目录结构

- `md_to_pdf.py`：核心转换逻辑（CLI）
- `md_to_pdf_gui.py`：图形界面（可选择输入 MD 和输出 PDF）
- `md_to_pdf.exe`：CLI 可执行文件
- `md_to_pdf_gui.exe`：GUI 可执行文件

## 使用方式

### 1) 图形界面（推荐）

双击运行：

- `md_to_pdf_gui.exe`

然后：

1. 选择输入 Markdown 文件（`.md`）
2. 选择输出 PDF 路径（可不填，不填默认同名 `.pdf`）
3. 点击“开始转换”

### 2) 命令行

使用 Python：

- `python md_to_pdf.py 输入.md`
- `python md_to_pdf.py 输入.md 输出.pdf`

使用 EXE：

- `md_to_pdf.exe 输入.md`
- `md_to_pdf.exe 输入.md 输出.pdf`

## 依赖说明

- 必需：本机安装 Microsoft Edge 或 Google Chrome（用于无头打印 PDF）
- 可选 Markdown 渲染库：
  - `markdown`
  - `mistune`

若都未安装，程序会自动退化到内置简易 Markdown 渲染。

## 打包命令（开发者）

CLI 版：

- `python -m PyInstaller --onefile --name md_to_pdf md_to_pdf.py`

GUI 版：

- `python -m PyInstaller --onefile --windowed --name md_to_pdf_gui md_to_pdf_gui.py`
