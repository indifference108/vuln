# -*- coding: utf-8 -*-
"""生成 Vane/Perplexica SSRF 漏洞 CNVD 报送材料 docx"""
import os
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "CNVD报送材料_Vane模型提供商接口SSRF.docx")

doc = Document()
style = doc.styles["Normal"]
style.font.name = "SimSun"
style.font.size = Pt(11)


def h(t, lvl=1):
    doc.add_heading(t, lvl)


def p(t, bold=False):
    para = doc.add_paragraph()
    run = para.add_run(t)
    run.bold = bold
    return para


title = doc.add_heading("Vane（Perplexica）AI问答引擎模型提供商注册接口存在未授权SSRF漏洞 情况通报", 0)
title.alignment = WD_ALIGN_PARAGRAPH.CENTER

h("一、漏洞概述")
p("公网实例 http://8.159.154.189:3001（阿里云·上海，页面标题 “Chat - Perplexica”）部署的开源 AI 问答引擎 "
  "Vane（原名 Perplexica，GitHub 36,700+ stars，MIT 协议）存在未授权服务端请求伪造（SSRF）漏洞，对应公开编号 CVE-2026-9372"
  "（CWE-918，CVSS v3.1 9.1 严重）。该实例版本 ≤1.12.1，官方已于 2026-04 发布修复版本 1.12.2，但该公网实例至今未升级，仍可被利用。")
p("其模型提供商注册接口 POST /api/providers 无任何身份校验，且对用户提交的 config.baseURL 不做私网地址、"
  "协议与重定向校验，服务端主动向该地址发起 HTTP 请求（请求 {baseURL}/api/tags），并将目标响应内容随错误信息回显。"
  "攻击者无需登录、无需交互，即可利用该服务器探测内网服务、读取云元数据（169.254.169.254），"
  "或以该服务器为跳板对内网发起攻击。")

h("二、验证过程（2026-10-03 实测，全程无害）")
p("1. 浏览器访问 http://8.159.154.189:3001/ ，确认为 Perplexica AI 问答界面（标题 “Chat - Perplexica”）。")
p("2. 提交注册请求：POST /api/providers，body 为 "
  "{\"type\":\"ollama\",\"name\":\"cnvd-verify\",\"config\":{\"baseURL\":\"http://www.example.com\"}}。"
  "服务器响应 200，返回体 chatModels[0].name 字段回显："
  "“Unexpected token '<', \"<!doctype \"... is not valid JSON”——该片段即 example.com 首页内容，"
  "证明请求由目标服务器代为发起且响应被回传，SSRF 成立。")
p("3. 验证完成后已自动删除测试创建的 provider（DELETE /api/providers/{id}，返回 200），未做任何内网探测与写操作。")

h("三、影响范围与危害定级")
p("FOFA 测绘 title=\"Perplexica\" && country=\"CN\" 命中 30+ 个国内公网实例（51 个独立 IP），"
  "其中实测 8.159.154.189:3001 仍可被未授权利用；其他实例亦可能运行受影响版本。"
  "该类系统常被单位内部用于私有知识问答，一旦部署即可成为内网探针。")
p("CVSS v3.1 9.1（严重），向量 CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:H；CWE-918。"
  "机密性：可读取内网服务与云元数据响应；可用性：可对内部服务发起探测型请求；完整性：无直接影响（与公开评估一致）。")

h("四、复现步骤")
p("1. 访问 http://8.159.154.189:3001/ 打开 AI 问答页面；")
p("2. 向 http://8.159.154.189:3001/api/providers 发送 POST 请求（Content-Type: application/json），"
  "body：{\"type\":\"ollama\",\"name\":\"任意\",\"config\":{\"baseURL\":\"http://www.example.com\"}}；")
p("3. 观察响应 200 中 chatModels[].name 回显的目标响应片段（“Unexpected token '<’, \"<!doctype \"...”）；")
p("4. 验证脚本：poc/verify_vane_ssrf.py（自动判定并自动清理测试数据）。")

h("五、修复建议")
p("【临时缓解】1. 反向代理对 /api/providers 增加访问控制（仅管理来源或 Basic Auth）；"
  "2. 出口防火墙禁止应用容器访问 127.0.0.0/8、10.0.0.0/8、172.16.0.0/12、192.168.0.0/16、169.254.0.0/16。")
p("【根治修复】1. 升级 Vane 至 1.12.2+；2. 注册接口加鉴权；3. 对 baseURL 做协议白名单与私网地址段过滤、禁止跟随重定向；"
  "4. 错误信息不回显目标响应内容。")

h("六、验证纪律声明")
p("本次验证由发现者本人执行：仅使用 example.com 作为外部 canary，单实例单请求验证，全程只读，"
  "未做内网探测、未利用元数据读取、未执行任何写利用，测试数据已全部删除。")

h("七、证据清单")
p("1. 完整请求/响应记录（evidence/http-transcript.txt）；2. POC 脚本（poc/verify_vane_ssrf.py）；"
  "3. 复现录屏（浏览器访问 + 请求重放 + 回显 + 清理，发现者留存）；4. FOFA 国内实例测绘记录。")

doc.save(OUT)
print("saved:", OUT)
