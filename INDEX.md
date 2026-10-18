# E:\kimi 项目索引（CVE+CNVD 漏洞挖掘与报送）

> 主控文档：notes.md（漏洞总表/凭证/踩坑/扫描史/雷达，所有结论以它为准）
> 最近更新：2026-10-18（7.31 工具链部署）

## 目录地图

| 路径 | 内容 |
|---|---|
| `notes.md` | **项目大脑**：7.1-7.31 编年记录，开工先读 |
| `vulns/` | 定案案例 ×5 类：`RCE/` `SQL注入/` `SSRF/` `弱密钥/` `逆向/`（一洞一目录：report-zh/en + audit-findings + STATUS + evidence + poc） |
| `scan/` | 扫描脚本 `_*.py` + 结果池 `fofa_pool/` `subdomain_pool/` `codeintel/` |
| `scan/subdomain_pool/` | CT 子域池（2,189 子域）+ 探针结果 |
| `repos/vuln-repo` | **GitHub 同步库**（github.com/indifference108/vuln），每次定案/登记后 push |
| `repos/autocve` | AutoCVE（larlarua/AutoCVE）源码，待有 docker+LLM key 后一键部署 |
| `tools/autocve_skills` | AutoCVE 的 4 个审计 Agent（code-audit-finding/code-security/cve-report-writer/secknowledge） |
| `tools/autocve_report_templates` | CVE 报告模板库 |
| `tools/vulndb/` | 轻量漏洞库（KEV+NVD 缓存，SQLite）：`python vulndb.py kev|kevfind|search` |
| `HANDOFF_PROMPT.md` | 会话交接 prompt 模板 |

## 工具速查

| 工具 | 用法 |
|---|---|
| FOFA（WebBridge） | 会话 `fofa-carrier`，首页 textarea 注入法，脚本模板 `scan/_fofa_carrier2.py` |
| vulndb | `python E:\kimi\tools\vulndb\vulndb.py kev` 同步被利用漏洞目录 |
| CNVD 报告 | 用 `cve-cnvd-cnnvd-report` skill 出中英文报送材料 |
| 网络 | 一律代理 `127.0.0.1:7897`；教育网目标防火墙 reset 不重试 |

## 当前主线（用户 2026-10-16/18 钦定）

三大运营商（chinamobile/10086/unicom/chinaunicom/10010/chinatelecom/189/10000）+ 中央部委；
优先级：**0day/Nday 高危** > 弱密钥（设备类才给证）> RCE（拿 shell）> SSRF > 固件漏洞。
纪律：只读非武器化、宁少报不错报、死线不重挖（见 notes 各条「死线登记」）。

## 已登记资产（回锅候选）

- aTrust 27.0.0 @ 211.137.206.49（江苏电信证书）——待版本漏洞
- 方城视频集群 16 台海康 NVR（117.158.64.0/20，全部已改密）
- Serv-U 15.1 @ 117.158.73.46:81（CVE-2024-28995 不可验，无 Web Client 会话）
- 宁波嘉菲环保设备 Agile（主线外，弱口令实锤未报送）
