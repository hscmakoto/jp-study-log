#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
jp_log.py - 日语学习记录工具（纯标准库，零依赖）

用法:
  python scripts/jp_log.py                       # 交互式记录今天
  python scripts/jp_log.py -y                    # 今天学了，但不知道花了多久
  python scripts/jp_log.py -n                    # 今天没学（会记一笔"没学"）
  python scripts/jp_log.py --minutes 45          # 今天学了 45 分钟
  python scripts/jp_log.py --minutes 30 --note "N3 听力 3 篇，记 20 个词"
  python scripts/jp_log.py --date 2026-11-08 -n  # 补记某天没学
  python scripts/jp_log.py --undo                # 撤销最近一次记录（删掉今天）
  python scripts/jp_log.py --status              # 查看最近记录与统计

数据存放: data/logs/YYYY-MM-DD.md
  每个"学过的日子"一个文件；没学的日子不存文件（统计时视为缺勤）。
  文件格式是一个极简的 YAML-ish，方便手改，也方便脚本解析:

  ---
  date: 2026-11-09
  studied: true
  minutes: 40
  note: N3 听力 3 篇
  ---
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT / "data" / "logs"

FIELD_ORDER = ["date", "studied", "minutes", "note", "grammar", "vocab"]

# 交互式记录时的快捷输入
YES_WORDS = {"y", "yes", "1", "是", "学了", "学", "s"}
NO_WORDS = {"n", "no", "0", "否", "没学", "没", "x"}


def today() -> dt.date:
    """按本机日期。如果你想固定按日本时间，改成 timezone(timedelta(hours=9))。"""
    return dt.date.today()


def parse_date(text: str | None) -> dt.date:
    if not text:
        return today()
    return dt.date.fromisoformat(text.strip())


def log_path(d: dt.date) -> Path:
    return LOG_DIR / f"{d.isoformat()}.md"


def parse_log(path: Path) -> dict:
    """解析一个记录文件，返回字段字典。容忍手写的宽松格式。"""
    text = path.read_text(encoding="utf-8")
    m = re.search(r"^---\s*$(.*?)^---\s*$", text, re.S | re.M)
    body = m.group(1) if m else text
    entry: dict = {}
    for line in body.splitlines():
        line = line.rstrip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition(":")
        if not sep:
            continue
        key = key.strip().lower()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        entry[key] = value

    if not entry.get("date"):
        entry["date"] = path.stem
    studied_raw = str(entry.get("studied", "")).lower()
    studied = studied_raw in ("true", "yes", "1", "y", "是")
    minutes = None
    if entry.get("minutes") not in (None, "", "null"):
        try:
            minutes = int(float(entry["minutes"]))
        except ValueError:
            minutes = None
    # 有分钟数但没有 studied 字段，也算学过
    if "studied" not in entry and minutes is not None:
        studied = True

    out = {
        "date": entry.get("date"),
        "studied": studied,
        "minutes": minutes,
        "note": entry.get("note", "") or "",
        "grammar": entry.get("grammar", "") or "",
        "vocab": entry.get("vocab", "") or "",
    }
    return out


def load_entries() -> list[dict]:
    if not LOG_DIR.exists():
        return []
    entries = []
    for p in sorted(LOG_DIR.glob("*.md")):
        try:
            entries.append(parse_log(p))
        except Exception as e:  # 单个坏文件不影响整体
            print(f"[warn] 跳过无法解析的文件 {p.name}: {e}", file=sys.stderr)
    entries.sort(key=lambda e: e["date"])
    return entries


def write_log(d: dt.date, studied: bool, minutes: int | None,
              note: str = "", grammar: str = "", vocab: str = "") -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    def q(s: str) -> str:
        """需要加引号的值加双引号，避免冒号/井号搞乱解析。"""
        if not s:
            return ""
        if re.search(r"[:#\"']|^\s|\s$", s):
            return '"' + s.replace('"', '\\"') + '"'
        return s

    mins = "" if minutes is None else str(minutes)
    content = (
        "---\n"
        f"date: {d.isoformat()}\n"
        f"studied: {'true' if studied else 'false'}\n"
        f"minutes: {mins}\n"
        f"note: {q(note)}\n"
        f"grammar: {q(grammar)}\n"
        f"vocab: {q(vocab)}\n"
        "---\n"
    )
    path = log_path(d)
    path.write_text(content, encoding="utf-8", newline="\n")
    return path


def summarize(entries: list[dict]) -> dict:
    studied_days = [e for e in entries if e["studied"]]
    total_minutes = sum(e["minutes"] or 0 for e in studied_days)
    today_d = today()
    # 找到今天（或今天之前最近一个记录日）作为"当前"
    if entries:
        last = dt.date.fromisoformat(entries[-1]["date"])
        ref = min(today_d, last)
    else:
        ref = today_d

    # 截止到 ref（按记录范围）的连续学习天数
    studied_dates = {e["date"] for e in entries if e["studied"]}
    streak = 0
    cur = ref
    while cur.isoformat() in studied_dates:
        streak += 1
        cur -= dt.timedelta(days=1)

    def active_days_in(start: dt.date, end: dt.date) -> int:
        return sum(1 for e in entries
                   if start <= dt.date.fromisoformat(e["date"]) <= end and e["studied"])

    week_start = today_d - dt.timedelta(days=today_d.weekday())
    return {
        "recorded_days": len(entries),
        "studied_days": len(studied_days),
        "total_minutes": total_minutes,
        "total_hours": round(total_minutes / 60, 1),
        "streak": streak,
        "this_week": active_days_in(week_start, today_d),
    }


def status() -> None:
    entries = load_entries()
    if not entries:
        print("还没有任何记录。运行 python scripts/jp_log.py 开始记第一条吧！")
        return
    s = summarize(entries)
    print("=== 日语学习记录概览 ===")
    print(f"记录天数     : {s['recorded_days']}")
    print(f"学习天数     : {s['studied_days']}")
    print(f"累计时长     : {s['total_minutes']} 分钟（约 {s['total_hours']} 小时）")
    print(f"当前连续     : {s['streak']} 天")
    print(f"本周已学     : {s['this_week']} 天")
    print("\n最近 10 条：")
    for e in entries[-10:][::-1]:
        mark = "✅" if e["studied"] else "❌"
        mins = f"{e['minutes']} 分钟" if e["minutes"] is not None else "—"
        note = f"  {e['note']}" if e["note"] else ""
        print(f"  {e['date']} {mark} {mins}{note}")


def interactive(d: dt.date) -> int:
    if log_path(d).exists():
        ans = input(f"{d} 已有记录，要覆盖吗？[y/N] ").strip().lower()
        if ans not in YES_WORDS:
            print("已取消。")
            return 0

    learned = None
    while learned is None:
        raw = input(f"{d} 学了日语吗？[y/n] ").strip().lower()
        if raw in YES_WORDS:
            learned = True
        elif raw in NO_WORDS:
            learned = False
        else:
            print("请输入 y 或 n。")

    minutes = None
    note = grammar = vocab = ""
    if learned:
        raw = input("今天学了多久（分钟，可留空表示不知道）: ").strip()
        if raw:
            try:
                minutes = int(raw)
            except ValueError:
                print("不是数字，按“不知道”处理。")
        note = input("一句话备注（可留空）: ").strip()
        grammar = input("今天重点语法点（可留空）: ").strip()
        vocab = input("今天复习/新学词汇（可留空，例如：30）: ").strip()

    path = write_log(d, learned, minutes, note, grammar, vocab)
    print(f"\n已写入 {path.relative_to(ROOT).as_posix()}")
    print("下一步: python scripts/build_readme.py  生成主页 README")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="记录每天的日语学习情况")
    ap.add_argument("-d", "--date", help="记录哪天，默认今天，格式 YYYY-MM-DD")
    ap.add_argument("-y", "--studied", action="store_true", help="学了（不填时长）")
    ap.add_argument("-n", "--not-studied", action="store_true", help="没学")
    ap.add_argument("-m", "--minutes", type=int, help="学习时长（分钟）")
    ap.add_argument("--note", default="", help="一句话备注")
    ap.add_argument("--grammar", default="", help="重点语法")
    ap.add_argument("--vocab", default="", help="词汇量或词汇备注")
    ap.add_argument("--undo", action="store_true", help="删除最近一次记录")
    ap.add_argument("--status", action="store_true", help="查看统计")
    args = ap.parse_args()

    if args.status:
        status()
        return 0

    if args.undo:
        entries = load_entries()
        if not entries:
            print("没有记录可撤销。")
            return 1
        target = log_path(dt.date.fromisoformat(entries[-1]["date"]))
        target.unlink()
        print(f"已删除 {target.relative_to(ROOT).as_posix()}")
        return 0

    d = parse_date(args.date)

    if args.not_studied:
        write_log(d, False, None)
        print(f"已记录 {d}: 没学 ❌")
        return 0

    if args.studied or args.minutes is not None or args.note or args.grammar or args.vocab:
        studied = True
        write_log(d, studied, args.minutes, args.note, args.grammar, args.vocab)
        mins = f" {args.minutes} 分钟" if args.minutes is not None else ""
        print(f"已记录 {d}: 学习{mins} ✅")
        return 0

    return interactive(d)


if __name__ == "__main__":
    sys.exit(main())
