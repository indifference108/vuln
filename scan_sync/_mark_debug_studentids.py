# -*- coding: utf-8 -*-
"""在逐行验证表里标出「需要用户人工调试/验证」的学号，并生成纯调试清单。

只存本地，不推公开仓库（含真实学号）。
调试 = 用户本人人工破验证码 + 逐行试登录 + 录屏，脚本不代跑。
"""
import csv, os, json, re
from collections import Counter, defaultdict

BASE = r"E:\kimi\scan"
SRC = os.path.join(BASE, "逐行验证表_v2_20261111.csv")
MAIN = os.path.join(BASE, "逐行验证表_v3_20261111.csv")
DBG_CSV = os.path.join(BASE, "需调试学号清单_20261111.csv")
DBG_MD = os.path.join(BASE, "需调试学号清单_20261111.md")
SUMMARY = os.path.join(BASE, "fofa_pool", "studentid_debug_marks_20261111.json")

rows = list(csv.DictReader(open(SRC, encoding="utf-8-sig")))
base_cols = list(rows[0].keys())
new_cols = ["需调试", "调试序号", "密码实际值(你填)", "调试状态(你填)", "调试结果/录屏(你填)"]

n = 0
debug_rows = []
for r in rows:
    ok = r["形态提示"].startswith("学号形态")
    if ok:
        n += 1
        tag = "D%02d" % n
        r["需调试"] = "✅ 需你调试"
        r["调试序号"] = tag
        r["密码实际值(你填)"] = ""
        r["调试状态(你填)"] = ""
        r["调试结果/录屏(你填)"] = ""
        r["备注"] = (r.get("备注", "") + " ｜ 人工破验证码→试登录→录屏；命中即在状态列记「命中」并把 mp4 丢回漏洞目录").strip(" ｜")
        debug_rows.append(r)
    else:
        r["需调试"] = "— 跳过（%s）" % r["形态提示"].split("，")[0]
        r["调试序号"] = ""
        r["密码实际值(你填)"] = ""
        r["调试状态(你填)"] = ""
        r["调试结果/录屏(你填)"] = ""
    for c in new_cols:
        r.setdefault(c, "")

# 1) 主表 v3（全 82 行，带标记）
with open(MAIN, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=base_cols + new_cols)
    w.writeheader()
    w.writerows(rows)

# 2) 纯调试清单 CSV（只 71 行，列顺序按实际操作重排）
dbg_cols = ["调试序号", "账号", "登录URL", "密码公式", "密码实际值(你填)",
            "验证码", "来源公示页", "公示标题", "调试状态(你填)", "调试结果/录屏(你填)", "备注"]
out = []
for r in debug_rows:
    out.append({
        "调试序号": r["调试序号"], "账号": r["账号"], "登录URL": r["登录URL"],
        "密码公式": r["密码"], "密码实际值(你填)": "", "验证码": r["验证码"],
        "来源公示页": r["来源公示页"], "公示标题": r["公示标题"],
        "调试状态(你填)": "", "调试结果/录屏(你填)": "", "备注": r["备注"],
    })
with open(DBG_CSV, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=dbg_cols)
    w.writeheader()
    w.writerows(out)

# 3) Markdown 版：按来源公示页分组，便于一批一批试
groups = defaultdict(list)
for r in out:
    groups[r["来源公示页"]].append(r)

lines = [
    "# 需调试学号清单（2026-11-11）",
    "",
    "> 本文件含真实在校生学号，**只存本地，禁止推公开仓库**。",
    "> 「调试」= 你本人人工破验证码 → 逐行试登录 → 全程录屏；脚本未代跑任何一次登录。",
    "",
    "## 统一入口与规则（同单位闭环 ✅）",
    "",
    "| 项 | 值 |",
    "|---|---|",
    "| 登录 URL | `https://ehall.csmzxy.edu.cn/` → `https://authserver.csmzxy.edu.cn/authserver/login` |",
    "| 表单 action | `/authserver/login` |",
    "| 必带字段 | `username` `password` `captcha` `lt` `execution` `_eventId` `dllt` `cllt` `rememberMe` |",
    "| 账号 | 学号（新生为身份证件号） |",
    "| 密码 | 默认**身份证后六位**（字母大写）——公式，`密码实际值` 列需你本人填 |",
    "| 验证码 | **有**，需人工破 |",
    "| 规则出处 | [学校公开 PDF《网上办事服务大厅业务流程介绍》2.1](https://xxc.csmzxy.edu.cn/__local/6/0A/38/EB4DCBB8FA2CBE4887CCFB91023_D816AD06_16B9F3.pdf) |",
    "| 红线 | 单入口 ≤5 组、不翻阅真实用户数据、不爆破、录屏留证 |",
    "",
    "## 标记说明",
    "",
    "| 分类 | 行数 | 处理 |",
    "|---|---:|---|",
    "| ✅ 需你调试 | %d | 本清单全部列出，逐行试 |" % len(out),
    "| — 跨单位仅留存 | 9 | 地大/昆理工/西电学号，配不上本入口，不试 |",
    "| — 疑似 QQ/电话 | 2 | `1565499207`、`1063034336`，跳过 |",
    "",
    "状态列可填：`待试` / `命中` / `失败` / `验证码挡住` / `强制改密`。",
    "",
    "## 逐行清单（按来源公示页分组）",
    "",
]
for url, rs in groups.items():
    t = (rs[0]["公示标题"] or "").strip()
    if not t or t in ("(首页)", "首页"):
        t = "首页公示表（%s）" % url.rstrip("/").split("/")[-1]
    lines.append("### %s · %d 个" % (t, len(rs)))
    lines.append("")
    lines.append("`%s`" % url)
    lines.append("")
    lines.append("| 调试序号 | 账号 | 密码实际值(你填) | 调试状态(你填) | 调试结果/录屏(你填) |")
    lines.append("|---|---|---|---|---|")
    for r in rs:
        lines.append("| %s | `%s` |  |  |  |" % (r["调试序号"], r["账号"]))
    lines.append("")

lines += [
    "## 被排除的 11 行（不必调试）",
    "",
    "| 原序号 | 账号 | 形态提示 |",
    "|---|---|---|",
]
for r in rows:
    if r["需调试"].startswith("✅"):
        continue
    lines.append("| %s | `%s` | %s |" % (r["序号"], r["账号"], r["形态提示"]))
lines.append("")
open(DBG_MD, "w", encoding="utf-8").write("\n".join(lines))

# 4) 不含真实学号的摘要（可同步仓库）
summary = {
    "ts": "2026-11-11 00:25",
    "source_table": "E:/kimi/scan/逐行验证表_v2_20261111.csv",
    "main_marked_table": "E:/kimi/scan/逐行验证表_v3_20261111.csv",
    "debug_only_csv": "E:/kimi/scan/需调试学号清单_20261111.csv",
    "debug_only_md": "E:/kimi/scan/需调试学号清单_20261111.md",
    "total_rows": len(rows),
    "marked_need_debug": len(out),
    "skipped": dict(Counter(r["形态提示"] for r in rows if not r["需调试"].startswith("✅"))),
    "groups": {u: len(v) for u, v in groups.items()},
    "marks_added": new_cols,
    "boundary": "真实学号只存本地；含号码的 CSV/MD 不入公开仓库；登录验证由用户本人录屏",
}
json.dump(summary, open(SUMMARY, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

print("主表 v3:", MAIN, len(rows), "行，新增列", new_cols)
print("需调试:", len(out), "行 →", DBG_CSV)
print("Markdown:", DBG_MD)
print("分组:", {os.path.basename(u): len(v) for u, v in groups.items()})
print("跳过:", dict(Counter(r["形态提示"] for r in rows if not r["需调试"].startswith("✅"))))
