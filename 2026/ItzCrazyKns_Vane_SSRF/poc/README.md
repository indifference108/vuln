# POC 使用说明

## 文件清单

| 文件 | 说明 |
|------|------|
| `verify_vane_ssrf.py` | 主验证脚本（推荐）。live 模式对真实授权目标验证；lab 模式离线完整复现。纯标准库，Python 3.8+。 |
| `mock-llm.mjs` / `canary-server.mjs` | Node.js 版的 mock LLM 与 canary 服务（与本次复现使用的原始脚本一致，等价于 `verify_vane_ssrf.py lab` 内嵌的 Python 实现）。 |

## 模式一：lab（离线完整复现，推荐）

```bash
python verify_vane_ssrf.py lab
```

脚本会自动：
1. 在本机 loopback 拉起 canary 内网服务（默认 127.0.0.1:8787）；
2. 拉起 OpenAI 兼容 mock LLM（默认 127.0.0.1:8399/v1），在 researcher 第一次迭代时确定性返回 `scrape_url` 工具调用；
3. 打印 Vane 需要的 `data/config.json` 内容（把 `hash` 字段设为该配置对象的 SHA-256，见脚本输出说明）；
4. 等待你启动 Vane（另开终端：`npm i --legacy-peer-deps && npx playwright install chromium-headless-shell && npm run dev`）；
5. 自动发送攻击请求并判定：canary 收到 Playwright UA 请求 + 响应含 canary 标记 = 复现成功。

## 模式二：live（对真实授权目标验证）

```bash
# 通过 Burp 逐包分析（默认即走 Burp）
USE_BURP=1 BURP_PROXY=http://127.0.0.1:8080 \
TARGET=http://vane.example.com \
CANARY_URL=http://YOUR-CANARY/internal-probe \
CANARY_TOKEN=your_unique_token \
PROVIDER_ID=<Vane 中已配置的供应商 id> \
CHAT_MODEL=<模型 key> EMBED_MODEL=<模型 key> \
python verify_vane_ssrf.py live
```

- `CANARY_URL` 必须是你控制的服务地址（OOB 域名或授权内网 canary），成功判据是该地址收到来自目标服务器的请求、且 `/api/search` 响应回显 `CANARY_TOKEN`。
- 真实 LLM 对「调用 scrape_url」的遵从度因模型/提示词而异，若未触发可换更明确的指令重试。

## 安全声明

仅用于授权测试与漏洞验证。脚本不实现任何攻击载荷、回连或持久化逻辑；全部操作为只读。
