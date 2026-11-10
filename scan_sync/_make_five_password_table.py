# -*- coding: utf-8 -*-
"""生成「学号 + 密码」五组验证表（CSV + Markdown），只存本地，不推公开仓库。

每个学号配 5 组可直接填写的候选口令；另单列官方公示规则（需自备证件号）。
按每 5 个学号一批分组，方便明早一批一批手动试。
"""
import csv, json, os, re

BASE = r"E:\kimi\scan"
SRC = os.path.join(BASE, "需调试学号清单_20261111.csv")
CSV_OUT = os.path.join(BASE, "学号密码五组表_20261111.csv")
MD_OUT = os.path.join(BASE, "学号密码五组表_20261111.md")
POOL = os.path.join(BASE, "fofa_pool")
SUMMARY = os.path.join(POOL, "five_password_table_summary_20261111.json")

ENTRY = "https://ehall.csmzxy.edu.cn/"
ENTRY_ALT = "https://jwxt.csmzxy.edu.cn/"
OFFICIAL = "{{身份证后六位}}（X 大写）"
OFFICIAL_SRC = "https://xxc.csmzxy.edu.cn/__local/6/0A/38/EB4DCBB8FA2CBE4887CCFB91023_D816AD06_16B9F3.pdf 《网上办事服务大厅业务流程介绍》2.1"

# 5 组：全部是可以直接填进密码框的具体值，按「依据强度」排序
GROUPS = [
    ("G1", "学号全号", "同类公开兜底",
     "长江师范学院试运行通知：身份证后六位无法登录则用学号或职工号；行业惯例也有「学号全号」",
     lambda s: s),
    ("G2", "学号后六位", "第三方公开资料",
     "公开资料提到该校教务初始密码「身份证号后6位或学号后6位」；同类高校常见截位",
     lambda s: s[-6:]),
    ("G3", "学号后八位", "推测·无本校准据",
     "同类「学号后 N 位」截位变体，该校无公示依据",
     lambda s: s[-8:]),
    ("G4", "123456", "通用弱口令",
     "国内高校教务/统一身份最常见的默认弱口令，该校无公示依据",
     lambda s: "123456"),
    ("G5", "000000", "通用弱口令",
     "同上，仅作最后兜底；命中与否都不作为报送主证据",
     lambda s: "000000"),
]

rows = list(csv.DictReader(open(SRC, encoding="utf-8-sig")))
# 只保留标记过的 71 行（清单本身就是 71 行），按原顺序
assert rows and len(rows) == 71, "预期 71 行待调试清单"

COLS = ["批次", "调试序号", "学号", "组号", "密码", "依据级别", "规则说明",
        "官方规则(需自备证件号)", "登录URL", "备用入口", "验证码",
        "来源公示页", "状态(你填)", "录屏/结果(你填)"]

# 00:56 自动验证已试过 D01 的「学号全号」，标出来避免明早重复试
pre_tested = {r["账号"]: r["调试状态(你填)"].strip()
              for r in rows if r["调试状态(你填)"].strip()}

out = []
for i, r in enumerate(rows):
    batch = i // 5 + 1
    sid = r["账号"]
    for gid, name, basis, note, fn in GROUPS:
        pre = ""
        if gid == "G1" and sid in pre_tested:
            pre = "已试失败（00:56 自动验证，规则 R2=学号全号）"
        out.append({
            "批次": "B%02d" % batch,
            "调试序号": r["调试序号"],
            "学号": sid,
            "组号": gid,
            "密码": fn(sid),
            "依据级别": basis,
            "规则说明": "%s ｜ %s" % (name, note),
            "官方规则(需自备证件号)": OFFICIAL,
            "登录URL": ENTRY,
            "备用入口": ENTRY_ALT,
            "验证码": "首屏隐藏；连续失败后弹出，需人工识别",
            "来源公示页": r["来源公示页"],
            "状态(你填)": pre,
            "录屏/结果(你填)": "",
        })

with open(CSV_OUT, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=COLS)
    w.writeheader()
    w.writerows(out)

# ---- Markdown ----
L = [
    "# 学号 + 密码 五组验证表（2026-11-11）",
    "",
    "> **只存本地，禁止推公开仓库**（含真实学号）。明早本人手动逐行试，全程录屏。",
    "",
    "## 入口与规则",
    "",
    "| 项 | 值 |",
    "|---|---|",
    "| 主入口 | `%s` → `authserver.csmzxy.edu.cn/authserver/login` |" % ENTRY,
    "| 备用入口 | `%s`（教务系统，同一套统一身份认证） |" % ENTRY_ALT,
    "| 账号 | **学号**（新生为身份证件号） |",
    "| **官方公示密码** | **%s** —— 见 [学校公开 PDF](https://xxc.csmzxy.edu.cn/__local/6/0A/38/EB4DCBB8FA2CBE4887CCFB91023_D816AD06_16B9F3.pdf) 《网上办事服务大厅业务流程介绍》2.1 |" % OFFICIAL,
    "| 验证码 | 首屏不显示，连续失败后弹出，需人工识别 |",
    "| 单入口纪律 | **同一个学号最多试 5 组**，失败就换下一个，别硬撞锁定 |",
    "",
    "⚠️ **官方规则那一组优先级最高，但需要该生身份证后六位**；4 个公示名单页只公示学号+姓名，"
    "没有证件号，所以下面 5 组给的都是**能直接填的具体值**。若你手上有证件号，先试 `{{身份证后六位}}`，"
    "它才是报送时最硬的证据。",
    "",
    "⚠️ **账号激活死线**：该校 [账号激活页](https://authserver.csmzxy.edu.cn/retrieve-password/accountActivation/index.html) "
    "写明「请先激活账号，再进行统一身份认证登录；激活时请设置符合强度要求的密码」。"
    "若某学号尚未激活，则默认口令可能根本不存在 —— 试完 5 组都失败就标「未激活/强制改密」，别继续撞。",
    "",
    "## 五组密码规则",
    "",
    "| 组 | 口令 | 依据级别 | 出处 / 说明 |",
    "|---|---|---|---|",
]
for gid, name, basis, note, _ in GROUPS:
    L.append("| %s | %s | %s | %s |" % (gid, name, basis, note))
L += [
    "",
    "**G1/G2 有公开出处，G3–G5 属推测或通用弱口令**；报送材料只认官方公示规则（身份证后六位）与实测录屏，"
    "G3–G5 命中也需回到规则本身补证。",
    "",
    "## 逐行验证表（按 5 个学号一批，共 %d 批 / %d 行）" % ((len(rows) + 4) // 5, len(out)),
    "",
]

for i, r in enumerate(rows):
    if i % 5 == 0:
        L += ["### 第 %d 批（学号 %d–%d）" % (i // 5 + 1, i + 1, min(i + 5, len(rows))), ""]
    L += [
        "**%s ｜ 学号 `%s`** ｜ 来源：[%s](%s)" %
        (r["调试序号"], r["账号"], (r["公示标题"] or "公示页")[:40], r["来源公示页"]),
        "",
        "| 组 | 密码 | 依据级别 | 状态(你填) | 录屏/结果(你填) |",
        "|---|---|---|---|---|",
    ]
    for gid, name, basis, note, fn in GROUPS:
        pre = "已试失败" if (gid == "G1" and r["账号"] in pre_tested) else ""
        L.append("| %s | `%s` | %s | %s |  |" % (gid, fn(r["账号"]), basis, pre))
    L.append("")

L += [
    "## 尝试顺序建议",
    "",
    "1. 有证件号 → 先试 `{{身份证后六位}}`（官方规则），命中即停并录屏。",
    "2. 没有 → 同一学号按 G1 → G2 → G3 → G4 → G5 顺序试，**5 组用完就换下一个学号**。",
    "3. 弹出验证码就人工识别；提示「激活/首次登录必须修改密码」标为死线；提示账号锁定立即停。",
    "4. 命中行回填状态与 mp4 文件名，按 §6 六件套出报送包。",
    "",
]
open(MD_OUT, "w", encoding="utf-8").write("\n".join(L))

json.dump({
    "ts": "2026-11-11 01:58",
    "source": "需调试学号清单_20261111.csv (71 rows)",
    "csv": "E:/kimi/scan/学号密码五组表_20261111.csv",
    "md": "E:/kimi/scan/学号密码五组表_20261111.md",
    "student_ids": len(rows), "groups_per_id": 5, "total_rows": len(out),
    "batches": (len(rows) + 4) // 5,
    "rules": [{"id": g[0], "name": g[1], "basis": g[2], "note": g[3]} for g in GROUPS],
    "official_rule": "ID-card last 6 (upper X), requires user-supplied data",
    "official_source": OFFICIAL_SRC,
    "alt_entry": ENTRY_ALT,
    "activation_deadline": "accountActivation page requires activation + self-set strong password before first login",
    "boundary": "real student IDs only in local files; no brute force beyond 5 sourced/generic candidates; user manually tries and records video",
}, open(SUMMARY, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

print("CSV:", CSV_OUT, len(out), "行")
print("MD :", MD_OUT)
print("批次数:", (len(rows) + 4) // 5, "| 学号数:", len(rows), "| 每学号 5 组")
print("第 1 批 5 个学号:", [r["账号"] for r in rows[:5]])
