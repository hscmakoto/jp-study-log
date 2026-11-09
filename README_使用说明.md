# 🇯🇵 日语学习日志

每天记录「今天学了/没学 + 学了什么」，自动展示在 GitHub 主页 README。

## 每天两步

```
双击 log.bat       → 记录今天（学了没、时长、备注）
双击 publish.cmd   → 重建 README 并推送到 GitHub
```

## 常用命令

```bat
python scripts\jp_log.py -y                              :: 今天学了，不记时长
python scripts\jp_log.py --minutes 40 --note "标日48课"   :: 学了 40 分钟
python scripts\jp_log.py -n                              :: 今天没学
python scripts\jp_log.py -d 2026-11-08 -n                :: 补记某天没学
python scripts\jp_log.py --undo                          :: 撤销最近一条
python scripts\jp_log.py --status                        :: 查看统计
python scripts\build_readme.py --months 12               :: 热力图改成 12 个月
```

补历史记录：

```bat
python scripts\import_history.py imports\历史.txt           :: 先预览
python scripts\import_history.py imports\历史.txt --write   :: 实际写入
```

格式：每段以 8 位日期 `YYYYMMDD` 开头（后面可以跟时间戳行，会被保留成来源注释）。

## 规则

- **严格模式**：没记录的日子算缺勤（⬛），中断连续天数
- **热力图从第一条记录开始画**，开始记录之前的日子不算缺勤（⬜）
- 未来日期是 ⬜，不计缺勤
- 历史记录没有时长是正常的，显示为 🟧「未计时」

## 配置位置

全部在 `scripts/build_readme.py` 顶部：

| 变量 | 作用 |
| :--- | :--- |
| `TITLE` / `INTRO` | 标题和引言 |
| `TIMEZONE_NOTE` | 显示在徽章下方 |
| `STRICT_MISSED` | `True` 严格模式 / `False` 宽容模式 |
| `WEEK_START_MONDAY` | 一周从周一开始 |
| `EMOJI_*` | 六种方块的颜色 |

## 目录

```
jp-study-log/
├── README.md                  # 自动生成，别手改
├── data/logs/YYYY-MM-DD.md    # 每日记录
├── imports/                   # 历史导入的原始文本（留档）
├── scripts/jp_log.py          # 记录 + 统计
├── scripts/build_readme.py    # 生成 README
├── scripts/import_history.py  # 导入历史记录
├── log.bat / publish.cmd      # 每天用的两个
├── init-repo.bat / push-first.bat  # 首次发布用，之后可删
└── .github/workflows/build-readme.yml  # 推送后自动重建
```

> 批处理脚本是纯 ASCII + CRLF 换行。**不要改成中文或 LF 换行**，否则 cmd.exe 报错。

## 记录文件格式

```markdown
---
date: 2026-11-09
studied: true
minutes: 240
note: 标日初级下47
grammar: 
vocab: 
---
```

手改也行，解析很宽松。`minutes` 留空 = 未计时。
