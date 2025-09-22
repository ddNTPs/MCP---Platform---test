# MCP Platform Demo

本项目提供一个可以在本地快速运行的示例，演示「客户系统接口 → MCP 平台 → Dify」的完整链路。所有服务均使用 Python 标准库实现，方便在任何环境下运行。

## 目录结构

- `customer_api/`：模拟客户系统对外开放的 HTTP 接口。
- `mcp_platform/`：对客户接口进行包装的 MCP 平台，实现统一返回格式、鉴权与审计。
- `dify_client/`：示例脚本，演示如何在 Dify 中以 HTTP Tool 方式调用 MCP 平台。
- `run_demo.py`：同时启动客户接口与 MCP 平台，方便体验。

## 快速开始

1. 启动两个服务：

   ```bash
   python run_demo.py
   ```

   终端会显示客户接口与 MCP 平台监听的地址：

   - 客户接口：<http://127.0.0.1:8001/api/orders>
   - MCP 平台：<http://127.0.0.1:8010/tools/orders>

   MCP 平台默认要求请求头中携带 `X-MCP-Key: mcp-demo-key`。

2. 打开新的终端窗口，演示一次 Dify（或任何 HTTP 调用方）的调用：

   ```bash
   python dify_client/demo_call.py
   ```

   你将看到 MCP 平台返回的标准化 JSON，其中包含原始数据与附加的元信息。

## 在 Dify 中接入

1. 在 Dify 后台创建一个「HTTP 请求」工具。
2. 填写 URL 为 `http://127.0.0.1:8010/tools/orders`。
3. 在 Headers 中增加 `X-MCP-Key: mcp-demo-key`。
4. 触发工具即可获取包装后的订单信息；如需查询单个订单，可在 URL 后追加订单号，例如 `http://127.0.0.1:8010/tools/orders/A1001`。

## 配置项

| 环境变量        | 默认值                      | 说明                           |
| --------------- | --------------------------- | ------------------------------ |
| `CUSTOMER_API_BASE` | `http://127.0.0.1:8001` | MCP 平台访问客户接口时使用的地址 |
| `MCP_API_KEY`       | `mcp-demo-key`            | MCP 平台校验请求头 `X-MCP-Key`  |

## 终止服务

运行 `run_demo.py` 的终端按下 `Ctrl+C` 即可优雅退出两个服务。

## 开发说明

项目不依赖任何第三方库，所有逻辑均在少量 Python 文件内实现，便于阅读与扩展。你可以根据业务需要补充更多工具端点、请求参数校验或审计机制。
