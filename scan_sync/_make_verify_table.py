# -*- coding: utf-8 -*-
"""生成逐行验证表（CSV + Markdown），只存本地，不推公开仓库。"""
import json, csv, time, os

SRC = r"E:\kimi\scan\fofa_pool\published_studentids_verified_20261111.json"
CSV = r"E:\kimi\scan\逐行验证表_20261111.csv"
MD = r"E:\kimi\scan\逐行验证表_20261111.md"

d = json.load(open(SRC, encoding="utf-8"))

# 同单位闭环入口（只读核实）
ENTRY = {
    "url": "https://ehall.csmzxy.edu.cn/",
    "redirect": "https://authserver.csmzxy.edu.cn/authserver/login?service=...",
    "action": "/authserver/login",
    "fields": "username / password / captcha / lt / execution / _eventId / dllt / cllt / rememberMe",
    "captcha": "有",
    "account_rule": "学号（新生为身份证件号）",
    "password_rule": "默认身份证后六位（字母大写）",
    "rule_source": "https://xxc.csmzxy.edu.cn/__local/6/0A/38/EB4DCBB8FA2CBE4887CCFB91023_D816AD06_16B9F3.pdf 《网上办事服务大厅业务流程介绍》2.1 登录方式",
}

other_rules = [
    ("南京铁道职院", "https://webvpn.njrts.edu.cn/", "{{学号/工号}}", "{{身份证后六位}}@njrts", "有"),
    ("南昌大学继教", "https://scept.ncu.edu.cn/", "{{身份证号}}或{{学号}}", "ncu@{{身份证后六位}}", "有"),
    ("西安科技大学", "https://ids.xust.edu.cn/", "{{学号}}", "{{身份证后六位}}；2016级前={{学号}}", "有"),
    ("兰州职院支付", "https://pay.lvu.edu.cn/", "{{学号}}", "{{身份证后六位}}", "有"),
    ("武汉城市职院支付", "https://jfxt.whcp.edu.cn/", "{{学号}}", "{{身份证后六位}}", "有"),
    ("天津师大研招", "https://yjszs.tjnu.edu.cn/", "{{准考证号}}", "{{居民身份证号(18位)}}", "有"),
    ("湖南物流职院图书馆", "https://library.hmlc.edu.cn/", "{{学号}}/{{工号}}", "{{身份证后六位}}", "无"),
    ("大连职院统一身份", "https://webvpn.dlvtc.edu.cn/", "{{10位学号}}", "{{原门户密码}}（未公开）", "有"),
    ("浙江工商大学研究生", "https://yjszhgl.zjgsu.edu.cn/", "{{学号}}", "ZJGSU#{{身份证倒数第7-2位}}", "有（强制改密，死线）"),
    ("某统一身份认证", "https://authservernew.caii.edu.cn/", "{{学号}}", "默认密码（未公示）", "有（强制改密，死线）"),
]

# 收集（学号, 来源页）
pairs = []
for s in d["sources"]:
    for p in s["pages"]:
        for sid in (p.get("student_ids") or []):
            pairs.append((sid, s["site"].split("//")[-1].rstrip("/"), p["title"], p["url"]))
seen = set(); uniq = []
for x in pairs:
    if x[0] not in seen:
        seen.add(x[0]); uniq.append(x)

rows = []
for i, (sid, site, title, url) in enumerate(uniq, 1):
    # 民职院学号 → 同单位闭环入口；其他单位学号 → 标注错配
    if "csmzxy.edu.cn" in site:
        rows.append({
            "序号": i, "单位": "长沙民政职院（同单位✅）", "登录URL": ENTRY["url"],
            "账号": sid, "密码": "{{身份证后六位}}", "验证码": ENTRY["captcha"],
            "来源公示页": url, "公示标题": title[:50],
            "备注": "规则来自学校公开PDF；密码需本人证件号后六位，未代填",
        })
    else:
        rows.append({
            "序号": i, "单位": site + "（跨单位❌）", "登录URL": "（需另找该单位入口）",
            "账号": sid, "密码": "（规则未公示）", "验证码": "—",
            "来源公示页": url, "公示标题": title[:50],
            "备注": "与10个规则站点不同单位，直接配对无效；仅作账号池留存",
        })

with open(CSV, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)

lines = [
    "# 逐行验证表（2026-11-11）",
    "",
    "> **只存本地，不推 GitHub 公开仓库**（真实学号属个人信息）。",
    "> 账号来自学校官网公开发布的评优/奖学金名单公示；密码列是**公示规则占位符**，不是已验证口令。",
    "> 登录验证请本人操作 + 录屏；单入口 ≤5 组、遇验证码即停（notes §9 / README 证据红线）。",
    "",
    "## A. 同单位闭环入口（可优先验证）",
    "",
    "| 项 | 值 |",
    "|---|---|",
    f"| 登录 URL | `{ENTRY['url']}` |",
    f"| 实际跳转 | `{ENTRY['redirect']}` |",
    f"| 表单 action / 字段 | `{ENTRY['action']}` / `{ENTRY['fields']}` |",
    f"| 账号规则 | {ENTRY['account_rule']} |",
    f"| 密码规则 | {ENTRY['password_rule']} |",
    f"| 验证码 | {ENTRY['captcha']}（需人工破） |",
    f"| 规则出处 | [学校公开 PDF]({ENTRY['rule_source'].split(' ')[0]}) 《网上办事服务大厅业务流程介绍》2.1 |",
    "",
    "## B. 逐行验证清单（82 个去重学号）",
    "",
    "| # | 单位 | 登录URL | 账号 | 密码 | 验证码 | 备注 |",
    "|---:|---|---|---|---|---|---|",
]
for r in rows:
    lines.append(f"| {r['序号']} | {r['单位']} | `{r['登录URL']}` | `{r['账号']}` | {r['密码']} | {r['验证码']} | {r['备注'][:34]} |")

lines += [
    "",
    "## C. 另外 10 个「公示初始密码规则」站点（账号需自备该单位公示名单）",
    "",
    "| 单位 | URL | 账号 | 密码 | 验证码 |",
    "|---|---|---|---|---|",
]
for n, u, a, p, c in other_rules:
    lines.append(f"| {n} | `{u}` | {a} | {p} | {c} |")
lines += ["", "完整 CSV：`E:\\kimi\\scan\\逐行验证表_20261111.csv`（utf-8-sig，Excel 可直接打开）。", ""]
open(MD, "w", encoding="utf-8").write("\n".join(lines))
print("CSV rows:", len(rows), "| 同单位:", sum(1 for r in rows if "✅" in r["单位"]),
      "| 跨单位:", sum(1 for r in rows if "❌" in r["单位"]))
print("saved", CSV, MD)
