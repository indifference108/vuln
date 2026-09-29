# CNVD 报送包 — zaidmukaddam Scira /api/proxy-image SSRF

> 渠道：cnvd.org.cn 实名注册 → 用户中心「提交漏洞」→ 选**通用型漏洞**（产品是开源软件，影响所有部署实例）。
> 依据：CNVD 报送指南（references/submission/cnvd.md）。

## 字段速填（与 report-zh.md 对应）

| 报送字段 | 值 |
|----------|-----|
| 漏洞名称 | zaidmukaddam Scira（截至 commit e1692f5）存在服务端请求伪造漏洞 |
| 漏洞类型 | 服务端请求伪造（SSRF，CWE-918） |
| 危害等级 | 高危（CVSS v3.1 7.5） |
| CVSS 分数/向量 | 7.5 / `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N` |
| 厂商 | zaidmukaddam（开源项目） |
| 产品 | Scira |
| 版本 | 截至 commit e1692f5（2026-08-13）的全部版本；项目无 Release/Tag |
| 漏洞描述 | 见 report-zh.md §3 |
| 影响范围 | 全部自部署实例及官方站点 scira.ai |
| 复现/验证过程 | 见 report-zh.md §8（四步，第三方可 1:1 复现） |
| 验证代码/POC | poc/scira-proxy-image-ssrf-nuclei.yaml、poc/poc.py（只读、脱敏、非武器化） |
| 修复建议 | 见 report-zh.md §10（临时缓解 + 根治修复） |

## 一级审核通过要点自查

- [x] 字段齐全、描述准确（report-zh.md 全文）
- [x] 通用型：提供通用验证方法（poc.py 任意实例可跑）+ 多实例佐证（自部署 WSL 实例 + 官方站 scira.ai）
- [x] 复现截图/报文：evidence/01-05（原始报文 + 脚本输出；截图可按 §8 步骤补拍后一并上传）
- [x] 原创性：CNVD 库检索「Scira」无记录；与 CVE/NVD/GitHub Advisory 无重复

## 红线确认

- 仅只读验证；生产站测试目标为自建 webhook.site 金丝雀，未触碰任何内网地址
- POC 无反弹 shell / 持久化 / 横向移动逻辑
- 按 CNVD 流程，厂商（maintainer）修复前不公开攻击细节

## 福利

通用型中危及以上可获 CNVD 电子《原创漏洞证明》与积分（bonus.cnvd.org.cn 兑换）。
