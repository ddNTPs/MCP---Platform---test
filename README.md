# MCP Platform Demo

本项目提供一个可以在本地快速运行的示例，演示「客户系统接口 → MCP 平台 → Dify」的完整链路。服务采用 Python 标准库实现，部署轻量。

## 目录结构

- `customer_api/`：模拟客户系统对外开放的 HTTP 接口。
- `mcp_platform/`：对客户接口进行包装的 MCP 平台，暴露符合 MCP HTTP 规范的工具并提供日志、降级能力。
- `dify_client/`：示例脚本，演示如何以 MCP HTTP 工具方式调用包装后的接口。
- `run_demo.py`：同时启动客户接口与 MCP 平台，方便体验。
- `tests/`：自动化用例验证端到端链路以及降级逻辑。

## 快速开始

1. 启动两个服务：

   ```bash
   python run_demo.py
   ```

   终端会显示以下信息：

   - 客户接口：<http://127.0.0.1:8001/api/orders>
   - MCP Manifest：<http://127.0.0.1:8010/.well-known/mcp.json>
   - MCP 工具端点：<http://127.0.0.1:8010/mcp/tools/orders>

   MCP 平台默认不校验 API Key，如需开启，可设置环境变量 `MCP_API_KEY`。

2. 新开一个终端验证调用：

   ```bash
   python dify_client/demo_call.py
   ```

   如输出中 `metadata.source` 为 `customer-api`，表示请求已经穿透到客户系统；若客户接口不可达，则会自动降级为 `sample-data`，依旧返回稳定的模拟数据。

## 在 Dify 中接入 MCP HTTP 服务

1. 在 Dify 后台选择「工具」→「MCP」→「添加 MCP 服务 (HTTP)」。
2. 将 URL 设置为 `http://127.0.0.1:8010`（注意填写服务根地址，Dify 会自动读取 `/.well-known/mcp.json`）。
3. 若启用了 API Key 校验，可在 Dify 中补充 `X-MCP-Key` 请求头。
4. 授权成功后即可在工作流或 Agent 中调用 `orders` 工具，获取订单列表或传入 `order_id` 查询单个订单。

> **提示**：即使客户接口暂不可用，MCP 平台也会返回内置的示例数据，保证接入过程中不会报错。

## 配置项

| 环境变量            | 默认值                    | 说明                               |
| ------------------- | ------------------------- | ---------------------------------- |
| `CUSTOMER_API_BASE` | `http://127.0.0.1:8001`   | MCP 平台访问客户接口时使用的地址   |
| `MCP_API_KEY`       | 未设置（不校验）         | MCP 平台校验请求头 `X-MCP-Key` 的值 |

## 终止服务

运行 `run_demo.py` 的终端按下 `Ctrl+C` 即可结束两个服务。

## 开发说明

项目不依赖第三方库，逻辑集中在少量 Python 文件中，便于理解和扩展。你可以在 MCP 平台中继续添加更多工具、审计字段或鉴权逻辑。
