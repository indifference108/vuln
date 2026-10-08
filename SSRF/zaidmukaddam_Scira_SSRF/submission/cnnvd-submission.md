# CNNVD 报送包 — zaidmukaddam Scira /api/proxy-image SSRF

> 渠道：cnnvd.org.cn 注册 → 「通用型漏洞报送」。
> 依据：CNNVD 报送指南（references/submission/cnnvd.md）。

## 字段速填（与 report-zh.md 对应）

| CNNVD 字段 | 值 |
|------------|-----|
| 漏洞名称 | zaidmukaddam Scira（截至 commit e1692f5）存在服务端请求伪造漏洞 |
| 漏洞类型 | 输入验证错误（SSRF，CWE-918；以表单动态字典中最贴切项为准） |
| 漏洞自评级 | 高危（2） |
| 厂商 / 受影响厂商 | zaidmukaddam |
| 受影响产品 | Scira |
| 受影响产品分类 | 应用软件 / Web 应用（AI 搜索引擎） |
| 受影响产品描述 | 见 report-zh.md §1 |
| 版本号（起始/结束） | 起始：未知（代码引入起）；结束：e1692f5（2026-08-13，main 最新） |
| 受影响实体原始链接 | https://github.com/zaidmukaddam/scira ；https://scira.ai |
| 漏洞描述或简介 | 见 report-zh.md §3 |
| 漏洞定位 | app/api/proxy-image/route.ts 第 19 行 fetch(url)（见 report-zh.md §4） |
| 漏洞触发条件 | 未授权远程访问 /api/proxy-image，url 参数指向内网地址（见 report-zh.md §8） |
| 漏洞影响描述 | 读取内网/回环/云元数据内容，机密性受损；可组合内网扫描、云凭证窃取、边缘缓存投毒 |
| CVE 编号 | 待分配（已准备 CVE 提交包，见 cve-submission.md） |
| 提交人 + 电话 + 邮箱 | {{待填}} |
| 技术支持联系电话 | {{待填，须与提交人不同}} |
| 附件 | poc/（zip ≤50MB）+ 验证输出 evidence/05（图片仅 JPG/PNG ≤5MB ≤3 张，可将关键输出截图后上传） |

## 提交前校验（官网规则）

- [ ] 提交人与技术支持联系人、电话、邮箱互不相同
- [ ] CVE/关联编号与描述一致（分配后回填）
- [ ] 图片附件 JPG/PNG ≤5MB ≤3 张；附件 zip/rar ≤50MB
- [ ] 相似度查重（checkNlp）：CNNVD 检索「Scira」无记录，可确认新漏洞继续提交

## PAV 映射（供系统归档）

`PAV:1.0:a:zaidmukaddam:scira:*`（应用类，版本范围至 e1692f5）
