# 审计发现：Vane（原 Perplexica）模型提供商注册接口未授权 SSRF

> 编号：VUL-2026-101
> 日期：2026-10-03
> 审计方式：黑盒审计（公开源码佐证调用链）+ 公网实例无害验证

## 1. 结论

Vane（原名 Perplexica，开源 AI 问答引擎，GitHub 36.7k stars，MIT 协议）的模型提供商注册接口 `POST /api/providers` 存在**未授权服务端请求伪造（SSRF，CWE-918）**。攻击者无需任何认证，通过提交恶意 `config.baseURL`，可使服务器向任意内网地址或云元数据服务发起 HTTP 请求，并将目标响应内容回显在错误信息中。受影响版本 ≤ 1.12.1（公开编号 CVE-2026-9372 / GHSA-cppx 系列）。

## 2. Source-to-Sink 调用链（依据公开源码，黑盒结果与其一致）

```
用户输入（POST /api/providers，JSON body 中的 config.baseURL）
  → 服务端 Provider 注册处理器（未鉴权：任意匿名请求可调用）
  → Ollama 类型 provider 初始化时向 baseURL + "/api/tags" 发起 fetch（无内网地址校验、无协议白名单、无重定向限制）
  → 响应体 JSON.parse 失败，异常信息连同目标响应片段一并写入 chatModels[].name 返回
```

## 3. 代码定位（公开仓库 ItzCrazyKns/Vane，v1.12.1 及之前）

```text
接口：src/app/api/providers/route.ts（POST 处理器）
Sink：服务端对 config.baseURL 直接发起 GET {baseURL}/api/tags
缺陷：baseURL 未做以下任何一项校验——
  1) 私网/保留地址段过滤（127.0.0.0/8、10.0.0.0/8、172.16.0.0/12、192.168.0.0/16、169.254.0.0/16）
  2) 协议白名单（http/https 之外，未限制 file/gopher/dict 等）
  3) 重定向跟随限制
  4) 注册接口本身无鉴权
```

## 4. 有效性判定（八项）

| 项 | 结论 |
|---|---|
| 可达 | ✅ 接口默认暴露，公网实例匿名可访问 |
| 可控 | ✅ baseURL 完全由攻击者控制 |
| 可传播 | ✅ 无任何中间校验打断 |
| 可利用 | ✅ 实测可让服务器取回 http://www.example.com 内容并回显 `<!doctype` 片段 |
| 防护可绕过 | ✅ 无防护可谈；docker 部署下 127.0.0.1 指向容器自身，可探测容器内服务 |
| 可复现 | ✅ 单条 POST 请求即可复现，见 evidence/http-transcript.txt |
| 影响成立 | ✅ 内网探测 + 云元数据（169.254.169.254）读取风险，响应内容回显降低利用门槛 |
| 影响范围 | ⚠️ 可与云元数据凭证读取组合扩大影响；已修复版本 >1.12.1 官方已发布 |

## 5. 黑盒验证摘要

- 目标实例：`http://8.159.154.189:3001`（阿里云·上海，标题 "Chat - Perplexica"）
- 请求：`POST /api/providers`，body `{"type":"ollama","name":"cnvd-verify","config":{"baseURL":"http://www.example.com"}}`
- 响应关键片段：`"name":"Unexpected token '<', \"<!doctype \"... is not valid JSON"`
- 判定：服务器已替攻击者完成对外请求并把响应内容回显 —— SSRF 成立。
- 测试数据已清理（DELETE /api/providers/{id}，返回 200 "Provider deleted successfully."）

## 6. 定性与定级

- CWE-918（Server-Side Request Forgery）
- CVSS v3.1：9.1（严重），`CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:H`
- 前提：无需认证、无需交互、公网可达
- 影响：C（读取内网服务与云元数据响应）、A（可对内网服务发起探测型请求造成压力）；I 记为 N 与公开 GHSA 评估一致
