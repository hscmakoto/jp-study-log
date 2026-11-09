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


def _quote(s: str) -> str:
    """需要加引号的值加双引号，避免冒号/井号搞乱解析。"""
    if not s:
        return ""
    if re.search(r"[:#\"']|^\s|\s$", s):
        return '"' + s.replace('"', '\\"') + '"'
    return s


def _append_text(old: str, new: str, sep: str = " / ") -> str:
    """把新内容接到旧内容后面；已经包含的片段不重复追加。"""
    new = (new or "").strip()
    if not new:
        return old or ""
    old = (old or "").strip()
    if not old:
        return new
    parts = [p.strip() for p in old.split(sep) if p.strip()]
    if new in parts:
        return old
    if new.startswith(old + " "):
        # 例如旧 note="标日初级下47"，新 note="标日初级下47 第2次" —— 保留更长的
        return new
    if old.startswith(new + " "):
        return old
    return f"{old}{sep}{new}"


def merge_entries(old: dict, new: dict) -> dict:
    """同一天两次记录合并：时长相加，备注拼接。"""
    if not old:
        return new
    if not new.get("studied"):
        # 今天已经记了"没学"或想改成没学：以"学过的"优先
        if old.get("studied"):
            return old
        return new
    merged = {
        "study_date": old.get("study_date") or new.get("study_date"),
        "studied": True,
        "minutes": None,
        "note": "",
        "grammar": "",
        "vocab": "",
    }
    vals = [old.get("minutes"), new.get("minutes")]
    real = [v for v in vals if v is not None]
    merged["minutes"] = sum(real) if real else None
    for field in ("note", "grammar", "vocab"):
        merged[field] = _append_text(old.get(field, ""), new.get(field, ""))
    return merged


def write_log(d: dt.date, studied: bool, minutes: int | None,
              note: str = "", grammar: str = "", vocab: str = "",
              mode: str = "merge") -> tuple[Path, dict]:
    """写一条记录。

    mode="merge"  同一天已有记录时累加时长、拼接备注（默认）
    mode="replace" 覆盖当天记录
    返回 (文件路径, 写入后的记录)。
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    path = log_path(d)

    new_entry = {
        "study_date": d.isoformat(),
        "studied": bool(studied),
        "minutes": minutes,
        "note": note or "",
        "grammar": grammar or "",
        "vocab": vocab or "",
    }

    final = new_entry
    if mode == "merge" and path.exists():
        try:
            old = parse_log(path)
            old = dict(old, study_date=old["date"])
            final = merge_entries(old, new_entry)
        except Exception:
            final = new_entry

    mins = "" if final["minutes"] is None else str(final["minutes"])
    content = (
        "---\n"
        f"date: {d.isoformat()}\n"
        f"studied: {'true' if final['studied'] else 'false'}\n"
        f"minutes: {mins}\n"
        f"note: {_quote(final['note'])}\n"
        f"grammar: {_quote(final['grammar'])}\n"
        f"vocab: {_quote(final['vocab'])}\n"
        "---\n"
    )
    path.write_text(content, encoding="utf-8", newline="\n")
    return path, final


def summarize(entries: list[dict]) -> dict:
    today_d = today()
    # 严格模式：没记录的日子视为缺勤，中断连续天数
    studied_dates = {e["date"] for e in entries if e["studied"]}
    total_minutes = sum(e["minutes"] or 0 for e in entries if e["studied"])

    last_studied = None
    if studied_dates:
        last_studied = dt.date.fromisoformat(max(studied_dates))
    streak = 0
    if last_studied and (today_d - last_studied).days <= 1:
        cur = today_d if today_d.isoformat() in studied_dates else today_d - dt.timedelta(days=1)
        while cur.isoformat() in studied_dates:
            streak += 1
            cur -= dt.timedelta(days=1)

    def active_days_in(start: dt.date, end: dt.date) -> int:
        if not entries:
            return 0
        first = dt.date.fromisoformat(entries[0]["date"])
        return sum(1 for day in (start + dt.timedelta(days=i)
                                 for i in range((end - start).days + 1))
                   if first <= day <= end and day.isoformat() in studied_dates)

    week_start = today_d - dt.timedelta(days=today_d.weekday())
    return {
        "recorded_days": len(entries),
        "studied_days": len(studied_dates),
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
    existing = None
    if log_path(d).exists():
        existing = parse_log(log_path(d))
        mins = f"{existing['minutes']} 分钟" if existing["minutes"] is not None else "未计时"
        note = f"，备注「{existing['note']}」" if existing["note"] else ""
        print(f"{d} 已有记录：{'学了' if existing['studied'] else '没学'} {mins}{note}")
        print("新内容会合并追加到今天的记录（时长相加，备注拼接）。")

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
        raw = input("这次学了多久（分钟，可留空表示不知道）: ").strip()
        if raw:
            try:
                minutes = int(raw)
            except ValueError:
                print("不是数字，按“不知道”处理。")
        note = input("这次学了什么（可留空）: ").strip()
        grammar = input("重点语法点（可留空）: ").strip()
        vocab = input("词汇量或词汇备注（可留空，例如：30）: ").strip()

    path, final = write_log(d, learned, minutes, note, grammar, vocab, mode="merge")
    print(f"\n已写入 {path.relative_to(ROOT).as_posix()}")
    if existing is not None:
        print(f"今日累计：{final['minutes'] if final['minutes'] is not None else '未计时'}"
              f"{' 分钟' if final['minutes'] is not None else ''}　"
              f"备注：{final['note'] or '—'}")
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
    ap.add_argument("--replace", action="store_true",
                    help="覆盖当天记录而不是合并（默认合并累加）")
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
    mode = "replace" if args.replace else "merge"

    if args.not_studied:
        if mode == "merge" and log_path(d).exists():
            old = parse_log(log_path(d))
            if old["studied"]:
                print(f"{d} 已记录为「学了」，不会改成没学。要强制改请加 --replace。")
                return 0
        path, final = write_log(d, False, None, mode=mode)
        print(f"已记录 {d}: 没学 ❌")
        return 0

    if args.studied or args.minutes is not None or args.note or args.grammar or args.vocab:
        path, final = write_log(d, True, args.minutes, args.note, args.grammar,
                                args.vocab, mode=mode)
        mins = f"{final['minutes']} 分钟" if final["minutes"] is not None else "未计时"
        print(f"已记录 {d}: 学习 ✅　今日累计 {mins}")
        if final["note"]:
            print(f"备注：{final['note']}")
        return 0

    return interactive(d)


if __name__ == "__main__":
    sys.exit(main())
