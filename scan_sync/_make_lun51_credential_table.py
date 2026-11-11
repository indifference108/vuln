# -*- coding: utf-8 -*-
"""生成「规则确定」的 lun51 凭据表（山东建筑大学，一手通知 + 本校公示学号姓名）。

规则来源：https://www.sdjzu.edu.cn/yjsc/info/1055/3330.htm （2026 秋季学期研究生学位论文形式规范检测通知）
  「系统网址 https://sdjzu.lun51.com/yjs；账号为学生学号，默认密码为姓氏拼音首字母大写
    加上学号后6位，如张三学号 2020135247 → Z135247；首次登录后请修改密码。」
英文版 https://www.lun51.com/homepage/...aid=348 写的是 "first capital letter of your name"（举例取名首字母），
故另外给一个「名首字母」变体列，两条都列、由验证结果裁决。

含真实姓名+学号，只存本地，不推公开仓库。
"""
import csv, json, os, re
from pypinyin import lazy_pinyin

BASE = r"E:\kimi\scan"
SRC = os.path.join(BASE, "_sdjzu_live_pairs.txt")     # 428 组「姓名 学号」
CSV_OUT = os.path.join(BASE, "确定规则_lun51凭据表_20261111.csv")
MD_OUT = os.path.join(BASE, "确定规则_lun51凭据表_20261111.md")
POOL = os.path.join(BASE, "fofa_pool")
SUMMARY = os.path.join(POOL, "lun51_deterministic_rule_summary_20261111.json")

ENTRY = "https://sdjzu.lun51.com/yjs"
RULE_URL = "https://www.sdjzu.edu.cn/yjsc/info/1055/3330.htm"
RULE_EN_URL = "https://www.lun51.com/homepage/index.php?m=home&c=View&a=index&aid=348"
KYC_URL = "山东建筑大学 2026 学术创新奖学金公示名单（scan/_sdjzu_jxj2026.docx）"


def initials(name):
    """返回 (姓首字母, 名首字母)，全大写。"""
    py = [p[0].upper() for p in lazy_pinyin(name) if p and p[0].isalpha()]
    if not py:
        return "", ""
    return py[0], (py[1] if len(py) > 1 else py[0])


pairs = []
for line in open(SRC, encoding="utf-8"):
    m = re.match(r"^\s*(\S+)\s+(\S+)\s*$", line)
    if not m:
        continue
    name, sid = m.group(1), m.group(2)
    if not re.match(r"^[A-Za-z0-9]{6,16}$", sid):
        continue
    pairs.append((name, sid))

rows = []
for i, (name, sid) in enumerate(pairs, 1):
    xing, ming = initials(name)
    tail = sid[-6:]
    main = xing + tail                    # 中文一手通知：姓首字母 + 学号后6位
    alt = ming + tail                     # 英文版歧义：名首字母 + 学号后6位
    rows.append({
        "序号": i,
        "姓名": name,
        "学号": sid,
        "登录账号": sid,
        "主密码(官方规则)": main,
        "备用密码(英文名首字母变体)": alt if alt != main else "",
        "学号后六位": tail,
        "登录URL": ENTRY,
        "验证码": "有（authorityCode，需人工识别）",
        "规则出处": RULE_URL,
        "KYC来源": KYC_URL,
        "状态(你填)": "",
        "录屏/结果(你填)": "",
    })

COLS = list(rows[0].keys())
with open(CSV_OUT, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=COLS)
    w.writeheader()
    w.writerows(rows)

L = [
    "# 规则确定 · lun51 凭据表（山东建筑大学）",
    "",
    "> **只存本地，禁止推公开仓库**（含真实姓名+学号）。",
    "",
    "## 这条为什么是「规则确定」",
    "",
    "| 环节 | 证据 |",
    "|---|---|",
    "| 一手规则 | [山东建筑大学研究生处 2026 秋季学期通知](%s) |" % RULE_URL,
    "| 原文 | 「账号为学生学号，**默认密码为姓氏拼音首字母大写加上学号后6位**，如张三学号 2020135247 则默认密码为 Z135247，首次登录后请修改密码」 |",
    "| 入口 | `%s`（实测 200 可达） |" % ENTRY,
    "| 账号源 | %s —— **428 组同校姓名+学号** |" % KYC_URL,
    "| 闭环 | 规则 / 账号 / 姓名 / 入口 **全部同单位**，不需要任何证件号，密码可直接算出 |",
    "| 英文版歧义 | [lun51 官方英文通知](%s) 写 \"first capital letter of your name\"，举例 `Daniel Zhang → D399910`（取**名**首字母）。中文版是「姓」，故本表两列都给 |" % RULE_EN_URL,
    "",
    "**对照**：长沙民政职院那条官方规则是「默认身份证后六位」，公示名单只有学号+姓名、没有证件号 → "
    "规则虽确定但**推不出完整凭据**；本表这条能直接算出完整账号+密码，所以应该先打它。",
    "",
    "## 风险与边界",
    "",
    "- 通知写明「首次登录后请修改密码」，且 2026 秋季检测窗口为 10/14–10/16，未登录过的账号才可能保留初始口令；"
    "**存活率未知，需实测**（同 §7.17 wsyps 的改密死线，但平台不同、规则不同，属于新维度，不算重复挖）。",
    "- 登录页有验证码 `authorityCode`（图源 oschina captcha），需人工识别；脚本不识别、不绕过。",
    "- 单账号最多 2 组（主密码 / 备用密码），失败即换号；命中立即停、录屏留证。",
    "- 不翻阅登录后的论文/个人信息，只判登录返回码。",
    "",
    "## 凭据表（%d 行）" % len(rows),
    "",
    "| # | 姓名 | 学号 | 主密码 | 备用 | 状态(你填) | 录屏(你填) |",
    "|---:|---|---|---|---|---|---|",
]
for r in rows[:0]:
    pass
for r in rows:
    L.append("| %d | %s | `%s` | `%s` | `%s` |  |  |" %
             (r["序号"], r["姓名"], r["学号"], r["主密码(官方规则)"],
              r["备用密码(英文名首字母变体)"] or "—"))
L += [
    "",
    "## 前 10 行速览",
    "",
    "| 姓名 | 学号 | 主密码 | 备用 |",
    "|---|---|---|---|",
]
for r in rows[:10]:
    L.append("| %s | `%s` | `%s` | `%s` |" %
             (r["姓名"], r["学号"], r["主密码(官方规则)"],
              r["备用密码(英文名首字母变体)"] or "—"))
L.append("")
open(MD_OUT, "w", encoding="utf-8").write("\n".join(L))

json.dump({
    "ts": "2026-11-11 14:30",
    "line": "lun51 deterministic default-password rule (Shandong Jianzhu University)",
    "rule": "capitalized first pinyin letter of SURNAME + last 6 digits of student ID",
    "rule_source": RULE_URL,
    "rule_en_ambiguous_source": RULE_EN_URL,
    "entry": ENTRY,
    "entry_status": "HTTP 200 reachable",
    "login_form": "account / password / authorityCode(captcha) -> POST /account/um_user/login/",
    "kyc_source": "2026 academic innovation scholarship roster, 428 name+ID pairs",
    "rows": len(rows),
    "candidates_per_account": 2,
    "why_priority": "official first-hand rule + same-unit public name/ID roster + reachable entry = fully derivable credentials, no ID-card number needed",
    "contrast": "csmzxy official rule = ID-card last 6, but rosters have no ID numbers -> not derivable",
    "risk": "notice says change password on first login; autumn window 10/14-10/16 passed; survival rate unknown",
    "boundary": "real names and IDs stay local only; captcha handled by human; max 2 attempts per account; no post-login data access",
}, open(SUMMARY, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

print("凭据表:", CSV_OUT, len(rows), "行")
print("MD   :", MD_OUT)
print("前 5 行:")
for r in rows[:5]:
    print("  ", r["姓名"], r["学号"], "主", r["主密码(官方规则)"], "备", r["备用密码(英文名首字母变体)"])
