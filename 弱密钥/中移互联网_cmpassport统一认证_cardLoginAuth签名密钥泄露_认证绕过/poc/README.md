# PoC 说明

本目录**不放可运行 PoC**。

原因：

1. 原始任务报告与报送包标注「内部／授权范围交付，禁止公开披露」，授权书硬约束含「不公开披露任何漏洞细节」。
2. 本仓库 `github.com/indifference108/vuln` 为**公开仓库**（2026-11-10 核实 `private=false`）。
3. 目标认证网关未确认修复，PoC 中包含可用签名密钥与完整签名公式，公开即可复现。

可运行 PoC 保留在本地，路径与校验值见 [../submission/报送材料清单.md](../submission/报送材料清单.md)：

- `CNVD复现-cardLoginAuth签名伪造.py`（Python 版）
- `CNVD复现-cardLoginAuth签名伪造.ps1`（PowerShell 版）
- `E:\kimi\ARTEX\data\tasks\15\i1921\verify.py`（最小对照验证脚本）

待厂商完成密钥轮换与修复、或授权方书面确认可披露后，再决定是否入库。
