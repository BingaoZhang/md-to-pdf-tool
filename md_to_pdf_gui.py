from __future__ import annotations

import argparse
import threading
from pathlib import Path
from tkinter import (
    BOTH,
    END,
    LEFT,
    RIGHT,
    W,
    Button,
    Entry,
    Frame,
    Label,
    StringVar,
    Tk,
    filedialog,
    messagebox,
)

from md_to_pdf import convert_markdown_file


class MdToPdfApp:
    def __init__(self, root: Tk) -> None:
        self.root = root
        self.root.title("Markdown 转 PDF 工具")
        self.root.geometry("760x230")
        self.root.minsize(700, 210)

        self.input_var = StringVar()
        self.output_var = StringVar()
        self.status_var = StringVar(value="请选择输入 Markdown 文件。")

        self._build_ui()

    def _build_ui(self) -> None:
        container = Frame(self.root, padx=14, pady=12)
        container.pack(fill=BOTH, expand=True)

        Label(container, text="输入 MD 文件：", anchor=W).pack(fill="x")
        input_row = Frame(container)
        input_row.pack(fill="x", pady=(4, 10))

        self.input_entry = Entry(input_row, textvariable=self.input_var)
        self.input_entry.pack(side=LEFT, fill="x", expand=True)
        Button(input_row, text="浏览...", width=11, command=self.choose_input).pack(
            side=RIGHT, padx=(8, 0)
        )

        Label(container, text="输出 PDF 路径（可选）：", anchor=W).pack(fill="x")
        output_row = Frame(container)
        output_row.pack(fill="x", pady=(4, 12))

        self.output_entry = Entry(output_row, textvariable=self.output_var)
        self.output_entry.pack(side=LEFT, fill="x", expand=True)
        Button(output_row, text="浏览...", width=11, command=self.choose_output).pack(
            side=RIGHT, padx=(8, 0)
        )

        action_row = Frame(container)
        action_row.pack(fill="x", pady=(0, 10))
        self.convert_btn = Button(
            action_row, text="开始转换", width=14, command=self.start_convert
        )
        self.convert_btn.pack(side=LEFT)
        Button(action_row, text="清空", width=10, command=self.clear_fields).pack(
            side=LEFT, padx=(8, 0)
        )

        self.status_label = Label(
            container, textvariable=self.status_var, anchor=W, fg="#2c3e50"
        )
        self.status_label.pack(fill="x")

    def choose_input(self) -> None:
        selected = filedialog.askopenfilename(
            title="选择 Markdown 文件",
            filetypes=[("Markdown 文件", "*.md"), ("所有文件", "*.*")],
        )
        if selected:
            self.input_var.set(selected)
            if not self.output_var.get().strip():
                self.output_var.set(str(Path(selected).with_suffix(".pdf")))
            self.status_var.set("已选择输入文件。")

    def choose_output(self) -> None:
        default_name = "output.pdf"
        input_path = self.input_var.get().strip()
        if input_path:
            default_name = Path(input_path).with_suffix(".pdf").name

        selected = filedialog.asksaveasfilename(
            title="选择输出 PDF 路径",
            defaultextension=".pdf",
            initialfile=default_name,
            filetypes=[("PDF 文件", "*.pdf")],
        )
        if selected:
            self.output_var.set(selected)
            self.status_var.set("已设置输出路径。")

    def clear_fields(self) -> None:
        self.input_entry.delete(0, END)
        self.output_entry.delete(0, END)
        self.status_var.set("已清空。请重新选择文件。")

    def start_convert(self) -> None:
        input_text = self.input_var.get().strip()
        output_text = self.output_var.get().strip()

        if not input_text:
            messagebox.showwarning("提示", "请先选择输入 Markdown 文件。")
            return

        self.convert_btn.config(state="disabled")
        self.status_var.set("正在转换，请稍候...")

        worker = threading.Thread(
            target=self._convert_worker,
            args=(input_text, output_text),
            daemon=True,
        )
        worker.start()

    def _convert_worker(self, input_path: str, output_path: str) -> None:
        try:
            out = convert_markdown_file(input_path, output_path or None)
            self.root.after(0, lambda: self._on_success(str(out)))
        except Exception as exc:
            self.root.after(0, lambda: self._on_error(str(exc)))

    def _on_success(self, out_path: str) -> None:
        self.convert_btn.config(state="normal")
        self.output_var.set(out_path)
        self.status_var.set(f"转换成功：{out_path}")
        messagebox.showinfo("完成", f"PDF 已生成：\n{out_path}")

    def _on_error(self, msg: str) -> None:
        self.convert_btn.config(state="normal")
        self.status_var.set("转换失败。")
        messagebox.showerror("错误", msg)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="GUI frontend for md_to_pdf.")
    parser.add_argument(
        "--self-test", action="store_true", help="Run headless self test"
    )
    return parser.parse_args()


def self_test() -> int:
    try:
        here = Path(__file__).resolve().parent
        candidate = here / "GEMM_实验报告.md"
        if not candidate.exists():
            return 0
        output = here / "GEMM_实验报告_gui_from_exe.pdf"
        convert_markdown_file(candidate, output)
        return 0 if output.exists() and output.stat().st_size > 0 else 1
    except Exception:
        return 1


def main() -> int:
    args = parse_args()
    if args.self_test:
        return self_test()

    root = Tk()
    app = MdToPdfApp(root)
    _ = app
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
