#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
import_history.py - 把历史学习记录导入 data/logs/

用法:
  python scripts/import_history.py history.txt           # 预览，不写文件
  python scripts/import_history.py history.txt --write   # 实际写入
  python scripts/import_history.py history.txt --write --force  # 覆盖已存在的日期

支持的输入格式（自动识别）:
  A. 两行式，日期行 + 内容行，交替出现:
       20261108
       标日初级下45
       20261106
       标日初级下44 ...
  B. 带时间戳的一行式（时间戳行会被忽略，日期以开头的 YYYYMMDD 为准）:
       2026-11-08 17:18:49 江苏
       标日初级下45

规则:
  - 日期取每段开头的 8 位数字 (YYYYMMDD)，不是内容里的时间戳
  - 同一日期出现多次时会合并备注
  - 没有天然时长的历史只记为 studied: true、minutes 留空（图表会用"未计时"颜色）
  - 每次导入都会把原始文本与来源时间戳保存进 note 的可回溯字段
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from jp_log import write_log, LOG_DIR, log_path  # noqa: E402

DATE_LINE = re.compile(r"^\s*(\d{4})(\d{2})(\d{2})\s*$")
META_LINE = re.compile(r"^\s*\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}(?::\d{2})?\s*(.*)$")


def parse(text: str) -> list[dict]:
    """把原始文本切成 [{date, items, meta}]，同一日期合并。"""
    segments: list[dict] = []
    cur: dict | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = DATE_LINE.match(line)
        if m:
            d = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
            cur = {"date": d, "items": [], "meta": []}
            segments.append(cur)
            continue
        if cur is None:
            continue  # 文件开头的杂项
        if META_LINE.match(line):
            cur["meta"].append(line)
            continue
        cur["items"].append(line)

    merged: dict[str, dict] = {}
    for seg in segments:
        entry = merged.setdefault(seg["date"], {"date": seg["date"], "items": [], "meta": []})
        for it in seg["items"]:
            if it not in entry["items"]:
                entry["items"].append(it)
        entry["meta"].extend(seg["meta"])
    return list(merged.values())


def build_entry(seg: dict) -> dict:
    note = " / ".join(seg["items"]) if seg["items"] else "(无内容)"
    # 页数 / 课时数等天然可数的动作，可在这里扩展；这里只保留原始文本
    return {
        "date": seg["date"],
        "studied": True,
        "minutes": None,
        "note": note,
        "grammar": "",
        "vocab": "",
        "meta": seg["meta"],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="历史记录文本文件（UTF-8）")
    ap.add_argument("--write", action="store_true", help="实际写入 data/logs/")
    ap.add_argument("--force", action="store_true", help="覆盖已存在的日期")
    args = ap.parse_args()

    src = Path(args.input)
    if not src.is_file():
        print(f"[error] 找不到文件: {src}", file=sys.stderr)
        return 1
    text = src.read_text(encoding="utf-8-sig")

    segs = parse(text)
    if not segs:
        print("[error] 没有解析出任何日期段，请检查格式", file=sys.stderr)
        return 1

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    existing = {p.stem for p in LOG_DIR.glob("*.md")}

    print(f"解析到 {len(segs)} 个日期段：\n")
    to_write = []
    for seg in segs:
        entry = build_entry(seg)
        flag = ""
        if entry["date"] in existing:
            flag = "  [已存在，需 --force 才覆盖]" if not args.force else "  [覆盖]"
        print(f"  {entry['date']}  {entry['note']}{flag}")
        if entry["meta"]:
            print(f"      源: {entry['meta'][0]}")
        if args.write and (args.force or entry["date"] not in existing):
            to_write.append(entry)

    # 日期顺序
    order = sorted({e["date"] for e in to_write})

    if not args.write:
        print(f"\n预览模式，未写文件。确认无误后加 --write 执行。")
        return 0

    for entry in to_write:
        d = __import__("datetime").date.fromisoformat(entry["date"])
        minutes = entry["minutes"]
        write_log(d, True, minutes, entry["note"], entry["grammar"], entry["vocab"])
        # 把来源时间戳追加成注释，保留可追溯性
        if entry["meta"]:
            p = log_path(d)
            extra = "\n".join(f"# 来源: {m}" for m in entry["meta"]) + "\n"
            p.write_text(p.read_text(encoding="utf-8") + extra, encoding="utf-8")
    print(f"\n已写入 {len(to_write)} 条。")
    print("下一步: python scripts/build_readme.py 重建主页")
    return 0


if __name__ == "__main__":
    sys.exit(main())
