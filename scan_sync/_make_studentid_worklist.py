# -*- coding: utf-8 -*-
"""生成公开公示名单的学号清单（仅本地保存，不推公开仓库）"""
import json, time

SRC = r"E:\kimi\scan\fofa_pool\published_studentids_verified_20261111.json"
OUT = r"E:\kimi\scan\公示名单学号清单_20261111.md"

d = json.load(open(SRC, encoding="utf-8"))
lines = [
    "# 公开公示名单里的明文学号（2026-11-11）",
    "",
    "> 来源均为学校官网自己公开发布的评优/奖学金名单公示页，只含学号，不含姓名/证件号。",
    "> **本清单仅存本地 `E:\\kimi\\scan\\`，不推送 GitHub 公开仓库**（真实在校生学号属个人信息）。",
    "> 用途：edusrc/CNVD 报送取证时的账号素材；登录验证仍需本人录屏。",
    "",
    "| # | 单位 | 公示页 | 公示标题 | 学号数 |",
    "|---|---|---|---|---:|",
]
idx = 0
detail = []
for src in d["sources"]:
    for p in src["pages"]:
        ids = p.get("student_ids") or []
        if not ids:
            continue
        idx += 1
        site = src["site"].split("//")[-1].rstrip("/")
        title = p["title"][:52]
        lines.append(f"| {idx} | `{site}` | [链接]({p['url']}) | {title} | {len(ids)} |")
        detail.append((idx, site, title, p["url"], ids))

lines += ["", "## 学号明细", ""]
for i, site, title, url, ids in detail:
    lines.append(f"### {i}. {site} — {title}")
    lines.append("")
    lines.append(f"来源：`{url}`")
    lines.append("")
    lines.append("```")
    # 每行 8 个，便于复制进 CSV
    for k in range(0, len(ids), 8):
        lines.append(" ".join(ids[k:k + 8]))
    lines.append("```")
    lines.append("")

lines += [
    "## 使用提示",
    "",
    "- 学号是「账号」这一半；还需要对应单位公示的**初始密码规则**才能闭环。",
    "- 本清单里的单位（长沙民政职院、中国地质大学等）与 §7.38 表里 10 个「公示初始密码规则」站点**不是同一单位**，直接配对无效。",
    "- 若要用，优先找该单位自己是否也公示了初始密码规则（同单位闭环），或由用户指定目标单位后重新检索。",
    "- 登录验证请走 `scan_sync/_weakpwd_login_template.py`（单入口 ≤5 组、遇验证码即停、不落地真实号码）+ 本人录屏。",
    "",
]
open(OUT, "w", encoding="utf-8").write("\n".join(lines))
print("saved", OUT, "pages", idx, "total ids", sum(len(x[4]) for x in detail))
