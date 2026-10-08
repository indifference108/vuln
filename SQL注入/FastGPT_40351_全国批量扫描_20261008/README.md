# FastGPT CVE-2026-40351 全国独立实例批量扫描（2026-10-08 夜）

## 结论
- FOFA 切片建池 500 主机（body="tryfastgpt.ai" / body="fastgpt.cn"，CN 切片优先）→ 确认 FastGPT 378 个 → **CVE-2026-40351 命中 254 个（root/Owner 账号接管）**，命中率 67%。
- 与 zxkedu 教育云（19 高校同一后端）模式不同，这些是**独立部署实例**，每个都是独立事件型报送素材。
- 验证方式严格只读：对照组（不存在用户名 root_ne_probe）→ 实验组 root {"$ne":""}，code 200 + token + user.team.memberName=Owner 定案；未执行任何登录后操作。

## 命中分类（evidence/fg_hits_classified.json）
| 类别 | 数量 | 说明 |
|---|---|---|
| 政府 .gov.cn | 3 | 武汉自规局 ai/zfxxgk（已报送）；**安陆市政府 msjx.anlu.gov.cn:3002（新）** |
| 重点企业域名 | 100 | 见下 |
| 纯 IP | 111 | 待归属确认（证书/反查） |
| 隧道/demo 噪音 | 已剔除 | cpolar、hemorn、czyjsgk、yinzuo、zxkedu 重复入口 |

## 高价值报送候选（按报送价值排序）
1. **安陆市人民政府 msjx.anlu.gov.cn:3002**（.gov.cn，政府门户）
2. **帆软软件 aisupport.fanruan.com:9001**（国内头部 BI 厂商，安全响应快）
3. **南孚电池 yxai.nanfu.com**（首页标题"南孚AI魔镜"，品牌直证）
4. **威高集团 adpw.weigaogroup.com:9042**（医疗器械龙头）
5. **杏树林医疗 ai. / qa-ai.xingshulin.com**（医疗数据，危害放大）
6. **达意隆 tech-long.com 4 子域**（crm/moa/oa/weixin，同一企业多处）
7. **中原地产 aikits.centanet.com**（地产中介龙头）
8. 苏州发改委 znzs.fgw.suzhou.com.cn:18080 未命中（不在 254 内，仅 fg 指纹）——注意别混淆
9. 药明/医药类 latest-fastgpt.pharmbrain.com、healthruway
10. 城建/轨交类 gzmetroarticle.com.cn（广州地铁物资）、fastgpt.cityfun.com.cn（城云）

## 复扫/复验
- 证据：`evidence/fg_national_probe.json`（逐目标对照组+实验组结果）
- 脚本：`evidence/bulk_probe_readonly.py`（增量落盘，参数 起始 结束）
- 单目标定案复验沿用 `..\武汉自规局_FastGPT登录NoSQLi_CVE-2026-40351\poc\` 的 check_cve_2026_40351.py

## 报送路径（与武汉线同模板）
归属确认（ICP/证书）→ 用户录屏（check_cve_2026_40351.py）→ gen_cnvd_docx.py 打包 docx+zip → 事件型表单（名称命令执行类→实际选未授权访问，NoSQLi 写"手工构造 JSON 报文"）→ 提交后更新 vuln-repo 并 push。

## 注意
- 254 个命中不必全报：**每批挑 3-5 个高价值目标**（gov/医疗/头部企业）即可，避免批量报送触发审核风控。
- zxkedu 相关命中是智学客同一后端，已在今夜另一条报送覆盖，勿重复。
- 纯 IP 111 个可用 certscan3.py / identify.py 做归属后再入库。
