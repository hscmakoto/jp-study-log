# README_使用说明

每天花 10 秒记录「今天学了/没学 + 学了多久」，用 GitHub 主页 README 自动展示。

## 这个方案长什么样

- **主页顶部**：4 个徽章（累计时长 / 学习天数 / 连续天数 / 本周进度）
- **学习热力图**：按月的日期网格，颜色方块表示当天学习时长
- **最近记录表**：最近 10 天的状态、时长、备注
- **月度统计**：每月学习天数、累计时长、平均时长

全部由 `scripts/build_readme.py` 从 `data/logs/*.md` 生成，无需外部服务、无需打包工具、无需数据库。

## 目录

```
jp-study-log/
├── README.md                  # 自动生成，别手改
├── data/logs/2026-11-09.md    # 每日记录（一个学习日一个文件）
├── scripts/jp_log.py          # 记录 + 统计
├── scripts/build_readme.py    # 生成 README
├── log.bat                    # Windows 双击记录（交互式）
├── publish.cmd                # 一键重建 + 提交 + 推送
├── init-repo.bat              # 首次 git 初始化 + 提交
└── .github/workflows/build-readme.yml
```

> 批处理脚本全部是纯 ASCII + CRLF 换行。**不要用中文命名或改成 LF 换行**，否则 cmd.exe 会乱码报错。

## 每天怎么用（Windows）

双击 `log.bat`，按提示回答：

```
2026-11-09 学了日语吗？[y/n] y
今天学了多久（分钟，可留空表示不知道）: 40
一句话备注（可留空）: N3 听力 3 篇
今天重点语法点（可留空）: ～ている
今天复习/新学词汇（可留空，例如：30）: 20
```

也可以用命令行参数快速记录（`log.bat` 会透传参数，例如 `log.bat --minutes 40 --note "听力"`）：

```bat
python scripts\jp_log.py -y                  :: 今天学了（不记时长）
python scripts\jp_log.py --minutes 40        :: 学了 40 分钟
python scripts\jp_log.py -n                  :: 今天没学
python scripts\jp_log.py --minutes 30 --note "听力" --vocab 20
python scripts\jp_log.py -d 2026-11-08 -n    :: 补记某天没学
python scripts\jp_log.py --undo              :: 撤销最近一条
python scripts\jp_log.py --status            :: 查看统计
```

注意：`log.bat` 已自动设置 `PYTHONUTF8=1`；直接跑 python 时如果中文乱码，先 `chcp 65001` 或设置 `PYTHONIOENCODING=utf-8`。

## 发布到 GitHub（独立仓库）

1. 双击 `init-repo.bat`，填 git 用户名 / 邮箱（第一次需要），完成初始化与首次提交。
   如果之前配过 `git config --global`，会直接跳过提问。
2. 在 github.com 新建**空的公开仓库** `jp-study-log`：**不要**勾选 README / .gitignore / license。
3. 在仓库页面复制 HTTPS 地址，然后在本文件夹执行：

```bat
git remote add origin https://github.com/<你的用户名>/jp-study-log.git
git push -u origin main
```

之后每天：`log.bat` 记录 → `publish.cmd` 推送。仓库里的 GitHub Actions 会自动重建 README。

### 把仓库入口放到个人主页

在个人主页 README 里加一句：

```markdown
## 日本語学習

[![学习日志](https://github-readme-stats.vercel.app/api/pin/?username=<你的用户名>&repo=jp-study-log)](https://github.com/<你的用户名>/jp-study-log)
```

### 方式 B：直接用「个人主页仓库」展示

把 `jp-study-log` 里的 `data/`、`scripts/`、`.github/` 拷进你的 `<用户名>/<用户名>` 仓库，再把生成出来的内容追加到该仓库的 README.md 里。这样主页直接显示热力图。

### 方式 C：不想公开记录文件

只提交生成好的 `README.md`，把 `data/` 加进 `.gitignore`。代价是记录/生成只能在本地跑。

## 自定义

- **换标题/引言/时区**：`scripts/build_readme.py` 顶部的 `TITLE`、`INTRO`、`TIMEZONE_NOTE`
- **改热力图月数**：`python scripts\build_readme.py --months 12`（默认 6）
- **改颜色分档**：`scripts/build_readme.py` 里的 `EMOJI_HEAVY/MEDIUM/LIGHT/SHORT/MISSED/NO_RECORD`
- **改「没学」的判定**：目前没记录 = 没学。如果你希望只有显式记录 `studied: false` 才算缺勤，日历里把 `EMOJI_NO_RECORD` 换成空格即可。
- **按日本时间记录**：`jp_log.py` 的 `today()` 改用 `datetime.now(timezone(timedelta(hours=9))).date()`

## 记录文件格式

`data/logs/2026-11-09.md`：

```markdown
---
date: 2026-11-09
studied: true
minutes: 40
note: N3 听力 3 篇
grammar: "～ている"
vocab: 20
---
```

手改也可以，脚本解析很宽松（缩进、空行、# 注释都容忍）。增删字段不影响 README 生成。

## 想升级时再做

- **真正的日历热力图**：GitHub README 只允许有限的 HTML，且会插入 `<wbr>`、限制内联样式，像素级对齐不可靠。现在这个「日期网格 + 颜色方块」方案在任何浏览器/手机上都不会错位。若一定要经典热力图，可接入第三方渲染服务或把页面发布到 GitHub Pages。
- **图表**：用 `mermaid` 画月度柱状图，GitHub 原生渲染，见下例：

  ````markdown
  ```mermaid
  xychart-beta
      title "每月学习天数"
      x-axis [2026-09, 2026-10, 2026-11]
      y-axis "天" 0 --> 31
      bar [24, 28, 9]
  ```
  ````

- **反思长文**：单独的 `posts/` 目录 + GitHub Pages / Quartz / Hexo，适合周末写复盘。
