# -*- coding: utf-8 -*-
"""
10 个「公示初始密码规则」目标的登录入口只读勘察（不发送任何登录请求）
只做 GET：提取登录表单 action / 字段名 / 验证码 / 是否纯学号可推导。
用于判断「哪些目标真的能用公示材料验证」，不落地任何真实学号/证件号。
"""
import json, re, time, requests, urllib3
urllib3.disable_warnings()
OUT = r"E:\kimi\scan\fofa_pool\edusrc_weakpwd_login_recon_20261110.json"
s = requests.Session(); s.trust_env = False
s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36"})

TARGETS = [
    ("南京铁道职院", "https://webvpn.njrts.edu.cn/", "初始密码=身份证后六位@njrts"),
    ("南昌大学继教", "https://scept.ncu.edu.cn/", "账号=身份证号或学号，密码=ncu@身份证后六位"),
    ("西安科技大学", "https://ids.xust.edu.cn/", "初始密码=身份证后六位（2016级前=学号）"),
    ("兰州职院支付", "https://pay.lvu.edu.cn/", "账号=学号，初始密码=身份证后六位"),
    ("武汉城市职院支付", "https://jfxt.whcp.edu.cn/", "用户名=学号，初始密码=身份证后六位"),
    ("天津师大研招", "https://yjszs.tjnu.edu.cn/", "用户名=准考证号，初始密码=居民身份证号"),
    ("湖南物流职院图书馆", "https://library.hmlc.edu.cn/", "账号=学号/工号，初始密码=身份证后六位"),
    ("大连职院统一身份", "https://webvpn.dlvtc.edu.cn/", "账号=10位学号，初始密码=原门户密码"),
    ("浙江工商大学研究生", "https://yjszhgl.zjgsu.edu.cn/", "首次登录强制改密（死线）"),
    ("某统一身份认证", "https://authservernew.caii.edu.cn/", "首次登录强制改密（死线）"),
]

def probe(name, url, rule):
    try:
        r = s.get(url, timeout=8, verify=False, allow_redirects=True)
        b = r.text[:250000]; low = b.lower()
        forms = []
        for fm in re.finditer(r"<form[^>]*>(.*?)</form>", b, re.I | re.S):
            tag = fm.group(0)[:400]
            act = re.search(r'action\s*=\s*["\']([^"\']*)', fm.group(0), re.I)
            method = re.search(r'method\s*=\s*["\']([^"\']*)', fm.group(0), re.I)
            fields = [x.group(1) for x in re.finditer(r'<input[^>]*name\s*=\s*["\']([^"\']+)', fm.group(1), re.I)]
            forms.append({"action": act.group(1)[:100] if act else "",
                          "method": (method.group(1).upper() if method else "GET"),
                          "fields": fields[:10]})
        low_txt = re.sub(r"<[^>]+>", " ", b); low_txt = re.sub(r"\s+", " ", low_txt).lower()
        captcha = any(k in low for k in ["captcha", "verifycode", "validatecode", "验证码", "kaptcha"])
        # 规则所需的凭据类型
        need_idcard = any(k in rule for k in ["身份证", "证件"])
        need_sid = "学号" in rule or "准考证" in rule
        return {"name": name, "url": url, "rule": rule, "status": r.status_code,
                "final_url": r.url[:130], "len": len(r.content),
                "forms": forms[:5], "form_count": len(forms),
                "captcha": captcha,
                "needs_idcard_last6": need_idcard,
                "needs_student_id": need_sid,
                "publicly_derivable_with_sid_only": need_sid and not need_idcard,
                "note": "只读 GET，未提交任何凭据"}
    except Exception as e:
        return {"name": name, "url": url, "rule": rule, "status": None,
                "err": type(e).__name__ + ":" + str(e)[:80]}

res = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"),
       "boundary": "只读 GET 登录页；未 POST、未提交凭据、未爆破、未落地真实学号/证件号",
       "items": []}
for n, u, rule in TARGETS:
    x = probe(n, u, rule)
    res["items"].append(x)
    print(n[:14].ljust(14), "->", str(x.get("status")).ljust(5),
          "forms", x.get("form_count"), "captcha", x.get("captcha"),
          "需证件后六位", x.get("needs_idcard_last6"),
          "纯学号可推导", x.get("publicly_derivable_with_sid_only"), flush=True)
    json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    time.sleep(1.3)
print("DONE", flush=True)
