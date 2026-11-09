#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_readme.py - 根据 data/logs/*.md 生成 GitHub 主页用的 README.md

生成内容:
  1. 顶部徽章（累计时长 / 学习天数 / 连续天数 / 本周）
  2. 月度日历热力图（最近 N 个月，纯 GitHub 原生支持，无需外部服务）
  3. 最近记录表格
  4. 月度统计

纯标准库，零依赖。运行: python scripts/build_readme.py
可选参数: --months 6   控制热力图覆盖最近几个月（默认 6）
"""

from __future__ import annotations

import argparse
import calendar
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from jp_log import load_entries, summarize  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"

# ----- 个性化配置：改这里就行 -----
TITLE = "🇯🇵 我的日语学习日志"
INTRO = (
    "> 每天学一点日语，把「学了 / 没学」如实记下来。\n"
    "> 这个主页由脚本从 `data/logs/` 下的每日记录自动生成。"
)
TIMEZONE_NOTE = "时区：Asia/Hong_Kong（UTC+8）"
WEEK_START_MONDAY = True
FIRST_WEEKDAY = 0 if WEEK_START_MONDAY else 6

# 热力图的方块，颜色深浅 = 当天学习时长
EMOJI_HEAVY = "🟩"   # ≥ 2 小时
EMOJI_MEDIUM = "🟦"  # ≥ 1 小时
EMOJI_LIGHT = "🟨"   # ≥ 30 分钟
EMOJI_SHORT = "🟧"   # 学了但不足 30 分钟 / 未计时
EMOJI_MISSED = "⬛"  # 有记录但没学
EMOJI_NO_RECORD = "⬜"  # 没记录


def level_emoji(entry: dict) -> str:
    if not entry["studied"]:
        return EMOJI_MISSED
    mins = entry["minutes"]
    if mins is None or mins < 30:
        return EMOJI_SHORT
    if mins >= 120:
        return EMOJI_HEAVY
    if mins >= 60:
        return EMOJI_MEDIUM
    return EMOJI_LIGHT


def month_block(year: int, month: int, by_date: dict[str, dict]) -> list[str]:
    """一个月渲染成一个代码块：星历行 + 每周两行（emoji 行 + 日期行）。

    > 注意：GitHub 的 markdown 渲染器会在任何字符间插入 <wbr>，
    > 所以像素级热力图在 README 里很难保证对齐。这里做成
    > "日期网格 + 颜色方块"，对不齐也不会错位，浏览器里永远可读。
    """
    cal = calendar.Calendar(firstweekday=FIRST_WEEKDAY)
    weeks = cal.monthdatescalendar(year, month)
    title = f"{year} 年 {month} 月"
    # 日期行：周一..周日 对应的日期数字，属于本月的用 1-31，不属于的留白
    header = ["一", "二", "三", "四", "五", "六", "日"] if WEEK_START_MONDAY \
        else ["日", "一", "二", "三", "四", "五", "六"]

    emoji_rows, date_rows = [], []
    for week in weeks:
        emoji_cells, date_cells = [], []
        for day in week:
            if day.month != month:
                emoji_cells.append("  " + EMOJI_NO_RECORD)
                date_cells.append("  " + f"{'':>2}")
                continue
            key = day.isoformat()
            entry = by_date.get(key)
            emoji_cells.append("  " + (EMOJI_NO_RECORD if entry is None else level_emoji(entry)))
            date_cells.append("  " + f"{day.day:>2}")
        emoji_rows.append("".join(emoji_cells))
        date_rows.append("".join(date_cells))

    lines = [f"── {title} ──"]
    lines.append("  " + "   ".join(header))
    for e_row, d_row in zip(emoji_rows, date_rows):
        lines.append(e_row)
        lines.append(d_row)
    return lines


def heatmap_section(entries: list[dict], months: int) -> str:
    if not entries:
        return "_还没有记录。_\n"
    by_date = {e["date"]: e for e in entries}
    last = max(dt.date.fromisoformat(e["date"]) for e in entries)
    slots = []
    y, m = last.year, last.month
    for _ in range(months):
        slots.append((y, m))
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    slots.reverse()

    out = ["```text"]
    for (y, m) in slots:
        out.append("")
        out.extend(month_block(y, m, by_date))
    out.append("```")
    return "\n".join(out) + "\n"


def legend() -> str:
    return (
        f"图例：{EMOJI_HEAVY} ≥2 小时　{EMOJI_MEDIUM} ≥1 小时　"
        f"{EMOJI_LIGHT} ≥30 分钟　{EMOJI_SHORT} 学了（未计时/不足 30 分钟）　"
        f"{EMOJI_MISSED} 没学　{EMOJI_NO_RECORD} 没记录\n"
    )


def recent_table(entries: list[dict], n: int = 10) -> str:
    rows = ["| 日期 | 状态 | 时长 | 备注 |", "| :--- | :--- | ---: | :--- |"]
    for e in entries[-n:][::-1]:
        status = "✅ 学了" if e["studied"] else "❌ 没学"
        mins = f"{e['minutes']} 分钟" if e["minutes"] is not None else "—"
        note = e["note"].replace("|", "\\|") if e["note"] else ""
        rows.append(f"| {e['date']} | {status} | {mins} | {note} |")
    return "\n".join(rows) + "\n"


def monthly_stats(entries: list[dict]) -> str:
    by_month: dict[str, dict] = {}
    for e in entries:
        key = e["date"][:7]
        d = by_month.setdefault(key, {"days": 0, "minutes": 0, "has_time": 0})
        if e["studied"]:
            d["days"] += 1
            if e["minutes"] is not None:
                d["minutes"] += e["minutes"]
                d["has_time"] += 1
    rows = ["| 月份 | 学习天数 | 累计时长 | 平均（有记录的日子） |",
            "| :--- | ---: | ---: | ---: |"]
    for key in sorted(by_month, reverse=True)[:6]:
        d = by_month[key]
        avg = f"{d['minutes'] // d['has_time']} 分钟" if d["has_time"] else "—"
        hours = d["minutes"] / 60
        total = f"{d['minutes']} 分钟（{hours:.1f}h）"
        rows.append(f"| {key} | {d['days']} 天 | {total} | {avg} |")
    return "\n".join(rows) + "\n"


def render(entries: list[dict], months: int) -> str:
    s = summarize(entries)
    badges = [
        f"![总时长](https://img.shields.io/badge/累计时长-{s['total_hours']}%20小时-blue)",
        f"![学习天数](https://img.shields.io/badge/学习天数-{s['studied_days']}%20天-green)",
        f"![连续](https://img.shields.io/badge/连续学习-{s['streak']}%20天-orange)",
        f"![本周](https://img.shields.io/badge/本周已学-{s['this_week']}%20天-informational)",
    ]
    parts = [
        f"# {TITLE}\n",
        f"{INTRO}\n",
        " ".join(badges) + "\n",
        f"_{TIMEZONE_NOTE}_\n",
        "## 📅 学习热力图\n",
        legend(),
        heatmap_section(entries, months),
        "## 🕒 最近记录\n",
        recent_table(entries) if entries else "_还没有记录。_\n",
        "## 📊 月度统计\n",
        monthly_stats(entries) if entries else "_还没有记录。_\n",
        "---\n",
        "<sub>本页由 `scripts/build_readme.py` 根据 `data/logs/` 自动生成，"
        "请勿直接手改。</sub>\n",
    ]
    return "\n".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--months", type=int, default=6, help="热力图显示最近几个月")
    args = ap.parse_args()
    entries = load_entries()
    README.write_text(render(entries, args.months), encoding="utf-8", newline="\n")
    print(f"已生成 {README.relative_to(ROOT).as_posix()}（{len(entries)} 条记录）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
