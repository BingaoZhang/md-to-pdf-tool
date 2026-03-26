from __future__ import annotations

import argparse
import html
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


HTML_TEMPLATE = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    body {{
      font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", Arial, sans-serif;
      line-height: 1.75;
      color: #1f2328;
      max-width: 900px;
      margin: 0 auto;
      padding: 32px 28px 48px;
      font-size: 15px;
      word-break: break-word;
    }}
    h1, h2, h3, h4, h5, h6 {{
      margin-top: 1.5em;
      margin-bottom: 0.6em;
      line-height: 1.35;
      page-break-after: avoid;
    }}
    h1 {{ font-size: 2em; border-bottom: 1px solid #d0d7de; padding-bottom: 0.3em; }}
    h2 {{ font-size: 1.5em; border-bottom: 1px solid #d0d7de; padding-bottom: 0.2em; }}
    h3 {{ font-size: 1.25em; }}
    p, ul, ol, blockquote, pre, table {{ margin: 0.8em 0; }}
    ul, ol {{ padding-left: 1.6em; }}
    li + li {{ margin-top: 0.25em; }}
    code {{
      font-family: Consolas, "Courier New", monospace;
      background: #f6f8fa;
      padding: 0.15em 0.35em;
      border-radius: 4px;
      font-size: 0.92em;
    }}
    pre {{
      background: #f6f8fa;
      border-radius: 8px;
      padding: 14px 16px;
      overflow-x: auto;
      white-space: pre-wrap;
    }}
    pre code {{
      background: transparent;
      padding: 0;
    }}
    blockquote {{
      border-left: 4px solid #d0d7de;
      padding: 0.1em 1em;
      color: #57606a;
      margin-left: 0;
    }}
    table {{
      border-collapse: collapse;
      width: 100%;
      display: block;
      overflow-x: auto;
    }}
    table th, table td {{
      border: 1px solid #d0d7de;
      padding: 6px 10px;
      text-align: left;
    }}
    hr {{
      border: none;
      border-top: 1px solid #d0d7de;
      margin: 24px 0;
    }}
    img {{ max-width: 100%; }}
    @page {{
      size: A4;
      margin: 18mm 14mm 18mm 14mm;
    }}
  </style>
</head>
<body>
{body}
</body>
</html>
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert Markdown file to PDF on Windows."
    )
    parser.add_argument("input", help="Input Markdown file path")
    parser.add_argument("output", nargs="?", help="Output PDF file path (optional)")
    return parser.parse_args()


def render_markdown(markdown_text: str) -> str:
    for renderer in (
        render_with_markdown_pkg,
        render_with_mistune,
        render_basic_markdown,
    ):
        try:
            return renderer(markdown_text)
        except Exception:
            continue
    raise RuntimeError("Markdown 渲染失败。")


def render_with_markdown_pkg(markdown_text: str) -> str:
    import markdown  # type: ignore

    return markdown.markdown(
        markdown_text,
        extensions=[
            "extra",
            "tables",
            "fenced_code",
            "toc",
            "sane_lists",
        ],
        output_format="html5",
    )


def render_with_mistune(markdown_text: str) -> str:
    import mistune  # type: ignore

    return mistune.html(markdown_text)


def render_basic_markdown(markdown_text: str) -> str:
    lines = markdown_text.splitlines()
    out: list[str] = []
    paragraph: list[str] = []
    in_code = False
    code_lines: list[str] = []
    list_type: str | None = None

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            text = " ".join(part.strip() for part in paragraph if part.strip())
            out.append(f"<p>{inline_markdown(text)}</p>")
            paragraph = []

    def flush_list() -> None:
        nonlocal list_type
        if list_type:
            out.append(f"</{list_type}>")
            list_type = None

    for raw_line in lines:
        line = raw_line.rstrip("\n")
        stripped = line.strip()

        if stripped.startswith("```"):
            flush_paragraph()
            flush_list()
            if not in_code:
                in_code = True
                code_lines = []
            else:
                code_html = html.escape("\n".join(code_lines))
                out.append(f"<pre><code>{code_html}</code></pre>")
                in_code = False
                code_lines = []
            continue

        if in_code:
            code_lines.append(line)
            continue

        if not stripped:
            flush_paragraph()
            flush_list()
            continue

        if stripped == "---" or stripped == "***":
            flush_paragraph()
            flush_list()
            out.append("<hr>")
            continue

        if stripped.startswith("#"):
            flush_paragraph()
            flush_list()
            level = min(len(stripped) - len(stripped.lstrip("#")), 6)
            content = stripped[level:].strip()
            out.append(f"<h{level}>{inline_markdown(content)}</h{level}>")
            continue

        if stripped.startswith(">"):
            flush_paragraph()
            flush_list()
            content = stripped[1:].strip()
            out.append(f"<blockquote><p>{inline_markdown(content)}</p></blockquote>")
            continue

        if stripped.startswith(("- ", "* ")):
            flush_paragraph()
            if list_type != "ul":
                flush_list()
                out.append("<ul>")
                list_type = "ul"
            out.append(f"<li>{inline_markdown(stripped[2:].strip())}</li>")
            continue

        ordered_body = stripped.split(". ", 1)
        if len(ordered_body) == 2 and ordered_body[0].isdigit():
            flush_paragraph()
            if list_type != "ol":
                flush_list()
                out.append("<ol>")
                list_type = "ol"
            out.append(f"<li>{inline_markdown(ordered_body[1].strip())}</li>")
            continue

        flush_list()
        paragraph.append(stripped)

    flush_paragraph()
    flush_list()
    if in_code:
        code_html = html.escape("\n".join(code_lines))
        out.append(f"<pre><code>{code_html}</code></pre>")

    return "\n".join(out)


def inline_markdown(text: str) -> str:
    escaped = html.escape(text)

    def replace_pair(src: str, token: str, open_tag: str, close_tag: str) -> str:
        parts = src.split(token)
        if len(parts) < 3:
            return src
        result: list[str] = []
        open_now = False
        for idx, part in enumerate(parts):
            result.append(part)
            if idx != len(parts) - 1:
                result.append(open_tag if not open_now else close_tag)
                open_now = not open_now
        return "".join(result)

    escaped = replace_pair(escaped, "**", "<strong>", "</strong>")
    escaped = replace_pair(escaped, "*", "<em>", "</em>")
    escaped = replace_pair(escaped, "`", "<code>", "</code>")
    return escaped


def build_html(markdown_path: Path, body_html: str) -> str:
    title = html.escape(markdown_path.stem)
    return HTML_TEMPLATE.format(title=title, body=body_html)


def find_browser() -> str | None:
    candidates = [
        shutil.which("msedge"),
        shutil.which("chrome"),
        shutil.which("chrome.exe"),
        shutil.which("msedge.exe"),
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]

    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(candidate)
    return None


def html_to_pdf(html_path: Path, pdf_path: Path) -> None:
    browser = find_browser()
    if not browser:
        raise RuntimeError(
            "未找到 Edge/Chrome。请先安装 Microsoft Edge 或 Google Chrome。"
        )

    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    file_url = html_path.resolve().as_uri()
    cmd = [
        browser,
        "--headless=new",
        "--disable-gpu",
        "--allow-file-access-from-files",
        "--no-pdf-header-footer",
        f"--print-to-pdf={pdf_path}",
        file_url,
    ]

    result = subprocess.run(cmd, capture_output=True, text=False)
    if result.returncode != 0:
        raw_output = result.stderr or result.stdout or b""
        stderr = decode_process_output(raw_output).strip()
        raise RuntimeError(f"浏览器生成 PDF 失败：{stderr}")

    if not pdf_path.exists() or pdf_path.stat().st_size == 0:
        raise RuntimeError("PDF 文件未成功生成。")


def decode_process_output(raw: bytes) -> str:
    for encoding in ("utf-8", "gbk", sys.getdefaultencoding()):
        try:
            return raw.decode(encoding)
        except Exception:
            continue
    return raw.decode("utf-8", errors="ignore")


def default_output_path(input_path: Path) -> Path:
    return input_path.with_suffix(".pdf")


def convert_markdown_file(
    input_path: str | Path, output_path: str | Path | None = None
) -> Path:
    input_path_obj = Path(input_path).expanduser().resolve()

    if not input_path_obj.exists():
        raise FileNotFoundError(f"输入文件不存在：{input_path_obj}")
    if input_path_obj.suffix.lower() != ".md":
        raise ValueError("输入文件必须是 .md 文件。")

    output_path_obj = (
        Path(output_path).expanduser().resolve()
        if output_path
        else default_output_path(input_path_obj)
    )

    markdown_text = input_path_obj.read_text(encoding="utf-8")
    body_html = render_markdown(markdown_text)
    full_html = build_html(input_path_obj, body_html)

    with tempfile.TemporaryDirectory(prefix="md_to_pdf_") as temp_dir:
        temp_html_path = Path(temp_dir) / f"{input_path_obj.stem}.html"
        temp_html_path.write_text(full_html, encoding="utf-8")
        html_to_pdf(temp_html_path, output_path_obj)

    return output_path_obj


def main() -> int:
    args = parse_args()
    try:
        output_path = convert_markdown_file(args.input, args.output)
        print(f"PDF 已生成：{output_path}")
        return 0
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
