# -*- coding: utf-8 -*-
"""
第三轮深挖：只对「真设备/真登录页」做只读 GET，抓登录页结构与版本串。
红线：只发 GET；不爆破、不发 POST、不执行 payload、不读真实数据。
目标：
  - 弱密钥：登录页明文硬编码口令 / 明确默认口令提示 / 无验证码的管理入口
  - RCE：Zimbra/Citrix 版本串，对照 KEV N-day 影响范围（仅版本比对，不利用）
"""
import json, time, re, os
import requests, urllib3
urllib3.disable_warnings()

OUT = r"E:\kimi\scan\fofa_pool\edusrc_r3_deep_20261110.json"
s = requests.Session(); s.trust_env = False
s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124 Safari/537.36"})

TARGETS = [
    ("access_ctrl", "https://door.gxmu.edu.cn/"),
    ("access_ctrl", "https://access.ybipc.edu.cn/"),
    ("access_ctrl", "https://smartaccess.hit.edu.cn/"),
    ("access_ctrl", "https://fk.sctbc.edu.cn/"),
    ("zimbra", "http://mail.cs.sjtu.edu.cn:8080/"),
    ("zimbra", "https://mail2.cs.sjtu.edu.cn/"),
    ("zimbra", "https://mail.acem.sjtu.edu.cn/"),
    ("zimbra", "https://mail.cs.sjtu.edu.cn/"),
    ("netscaler", "https://app.tsari.tsinghua.edu.cn/"),
    ("netscaler", "https://liesmarsvd.whu.edu.cn/"),
    ("netscaler", "https://ysythgw.bupt.edu.cn/"),
    ("netscaler", "https://cloud.shems.edu.cn/"),
]

def probe(group, url):
    try:
        r = s.get(url, timeout=8, verify=False, allow_redirects=True)
        b = r.text[:200000]
        low = b.lower()
        m = re.search(r"<title[^>]*>(.*?)</title>", b, re.I | re.S)
        title = re.sub(r"\s+", " ", m.group(1)).strip()[:100] if m else ""
        inputs = []
        for im in re.finditer(r"<input[^>]*>", b, re.I):
            tag = im.group(0)
            nm = re.search(r'name\s*=\s*["\']([^"\']+)', tag, re.I)
            tp = re.search(r'type\s*=\s*["\']([^"\']+)', tag, re.I)
            vl = re.search(r'value\s*=\s*["\']([^"\']*)', tag, re.I)
            inputs.append({"name": nm.group(1) if nm else "", "type": tp.group(1) if tp else "",
                           "value": vl.group(1)[:30] if vl else ""})
        # 明文硬编码口令线索（只读页面文本，不是爆破）
        hardcoded = [v["value"] for v in inputs
                     if v["type"].lower() == "password" and v["value"]]
        pwd_hint = [x for x in ["默认密码", "默认口令", "初始密码", "初始口令", "default password",
                                "admin/12345", "admin/admin", "密码为", "password is"]
                    if x.lower() in low]
        ver = re.findall(r"(?:Zimbra|NetScaler|Citrix Gateway|Build|Version)[^\n<]{0,50}?(\d+\.\d+(?:\.\d+)?)", b, re.I)[:5]
        captcha = any(x in low for x in ["验证码", "captcha", "validatecode", "verifycode"])
        return {"group": group, "url": url, "final_url": r.url[:140], "status": r.status_code,
                "len": len(r.content), "title": title,
                "ctype": r.headers.get("Content-Type", "")[:60],
                "server": r.headers.get("Server", "")[:60],
                "inputs": inputs[:14], "hardcoded_password_values": hardcoded,
                "default_pwd_hints": pwd_hint, "version_hints": ver,
                "has_captcha": captcha,
                "vendor_hints": [x for x in ["海康", "hikvision", "大华", "dahua", "中控", "zkteco",
                                             "熵基", "达实", "科士达", "zimbra", "citrix", "netscaler"]
                                 if x in low][:8]}
    except Exception as e:
        return {"group": group, "url": url, "status": None,
                "err": type(e).__name__ + ":" + str(e)[:90]}

res = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"),
       "boundary": "只读 GET 登录页；不 POST、不爆破、不执行 payload、不读真实数据",
       "items": []}
for g, u in TARGETS:
    r = probe(g, u)
    res["items"].append(r)
    print(g, u.split("//")[-1][:38], "->", r.get("status"), "|", (r.get("title") or "")[:38],
          "| hardcoded:", r.get("hardcoded_password_values"),
          "| hints:", r.get("default_pwd_hints"),
          "| ver:", r.get("version_hints"),
          "| vendor:", r.get("vendor_hints"), flush=True)
    json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    time.sleep(1.5)
print("DONE", len(res["items"]), flush=True)
