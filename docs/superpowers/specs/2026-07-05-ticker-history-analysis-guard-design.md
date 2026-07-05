# 股票历史分析提醒与运行阻断设计

## 背景

当前分析页点击“开始分析”后会直接创建新 run：

- 不会在启动前提醒用户该股票是否近期分析过。
- 不会在启动前阻断“同一只股票已经在分析中”的再次提交。
- 运行列表页已有 `status`、`signal` 等历史信息，但分析前没有复用。
- 运行详情页当前没有面向活动 run 的显式“停止分析”入口。

同时，用户本次明确要求：

- 同日同票要保持完全独立，不复用上一次分析结果。
- 如果该股票在今天、昨天、前天这 3 个自然日内分析过，再次分析前必须弹窗确认。
- 如果该股票当前仍有未结束分析，则不要允许重新分析，只能提示用户去查看当前分析。
- 弹窗中需要展示该股票全部历史分析记录，按 `10` 条一页分页。
- 历史记录点击后跳转到现有分析详情页查看结果。
- 分析列表页需要展示历史分析使用的模型供应商。

以当前对话日期 `2026-07-05` 为例，“3 天内”明确指：

- `2026-07-05`
- `2026-07-04`
- `2026-07-03`

而不是滚动的 `72` 小时窗口。

## 目标

- 在分析页启动前增加同票历史预检查。
- 为该股票提供专用历史记录接口，支持精确分页查询。
- 当同票存在活动 run 时阻断重新分析，并引导用户立即查看。
- 当同票在近 3 个自然日内分析过时弹出确认弹窗。
- 保持“同日同票完全独立”，避免多次 run 共用同一条 memory pending 记录。
- 在运行列表页展示模型供应商。
- 在运行详情页为 `queued` / `running` 记录补充手动停止能力。

## 非目标

- 不改变现有 run 详情页的主体布局与报告结构。
- 不改造成“弹窗内直接预览历史报告”。
- 不把运行列表的整体分组方式从“按公司卡片”改为“按 ticker 明细页”。
- 不改变现有新 run 的核心创建接口 `/api/runs` 的基本职责。
- 不支持在有活动 run 时排队创建同 ticker 的第二个新 run。

## 当前约束

### 分析页

- [`frontend/src/pages/AnalyzePage.vue`](../../../frontend/src/pages/AnalyzePage.vue) 的 `startRun()` 当前直接 `POST /api/runs`。
- 页面没有历史预检查，也没有弹窗确认步骤。

### 历史列表与详情

- [`frontend/src/pages/RunsPage.vue`](../../../frontend/src/pages/RunsPage.vue) 通过 `/api/runs/company-groups` 渲染按公司分组的近期 run 表格。
- [`frontend/src/pages/RunDetailPage.vue`](../../../frontend/src/pages/RunDetailPage.vue) 已支持通过 run 行跳转查看历史详情，也已经加载同 ticker 历史记录用于历史日历。

### 后端数据模型

- `GET /api/runs` 的 `RunSummary` 已经包含 `llm_provider`、`status`、`signal` 等字段。
- 现有接口缺少“按 ticker 精确分页查询历史记录”的专用入口。
- 当前 memory log 对同一 `(ticker, trade_date)` 的 `pending` 记录有幂等保护，会影响“同日同票完全独立”语义。

## 核心设计

### 1. 分析前预检查流程

分析页点击“开始分析”后的流程调整为：

1. 读取当前表单中的 `ticker`。
2. 调用新的 ticker-history 接口查询该股票历史记录与活动状态。
3. 根据返回结果分三种情况处理：

#### 情况 A：存在活动 run

活动 run 定义为 `status in {"queued", "running"}`。

行为：

- 弹出阻断弹窗。
- 标题明确说明“该股票正在分析中”。
- 表格展示该股票全部历史分析记录，`10` 条一页。
- 点击任意历史记录跳转到现有 `/runs/:runId` 详情页。
- 底部仅提供：
  - `立即查看`
  - `关闭`
- 不显示“启动新的分析”按钮。
- `立即查看` 默认跳转到活动 run；如果有多个活动 run，则跳最新一条。

#### 情况 B：无活动 run，但近 3 个自然日内分析过

行为：

- 弹出确认弹窗。
- 标题明确说明“该股票在近 3 天内已分析过，请确认是否继续”。
- 表格同样展示该股票全部历史分析记录，`10` 条一页。
- 点击任意历史记录跳转到 `/runs/:runId`。
- 底部提供：
  - `启动新的分析`
  - `关闭`
- 用户只有明确点击“启动新的分析”后才真正 `POST /api/runs`。

#### 情况 C：无活动 run，且近 3 个自然日内未分析过

行为：

- 不弹窗。
- 直接创建新的 analysis run。

### 2. “3 天内”规则

“3 天内”采用**前端所在环境本地自然日**判定，而不是 UTC 日界线，也不是 `72` 小时滑动窗口。

实现要求：

- 以浏览器本地日期生成 `today / yesterday / day before yesterday` 三个日期键。
- 将 ticker-history 返回的最新创建时间或逐条记录创建时间映射到本地日期后比较。
- 判定逻辑必须稳定支持用户当前时区，不依赖服务器部署时区。

示例：

- 若用户本地日期为 `2026-07-05`，则近 3 天窗口固定为 `2026-07-05`、`2026-07-04`、`2026-07-03`。

### 3. 新增 ticker-history 专用接口

新增接口：

- `GET /api/runs/ticker-history?ticker=<TICKER>&page=1&page_size=10`

用途：

- 为分析页启动前的同票预检查提供精确数据。
- 为弹窗中的历史表格提供分页数据。

返回结构：

```json
{
  "ticker": "NVDA",
  "company_name": "NVIDIA Corporation",
  "latest_created_at": 1783248000000,
  "has_active_run": true,
  "active_run_id": "run-123",
  "active_run_status": "running",
  "page": 1,
  "page_size": 10,
  "total_count": 27,
  "items": [
    {
      "run_id": "run-123",
      "status": "running",
      "ticker": "NVDA",
      "company_name": "NVIDIA Corporation",
      "date": "2026-07-05",
      "asset_type": "stock",
      "created_at": 1783248000000,
      "started_at": 1783248005000,
      "completed_at": null,
      "queue_position": null,
      "llm_provider": "openai",
      "archived": false,
      "signal": null,
      "error": null,
      "annotation": null,
      "review": null
    }
  ]
}
```

要求：

- `items` 按 `created_at desc` 排序。
- `page_size` 默认 `10`，上限 `100`。
- `ticker` 比较使用标准化大写值。
- 返回结果包含该股票**全部历史记录总数**，而不仅是近 3 天记录。
- “全部历史记录”包含 active 与 archived 两类 run，不因当前列表页的 archived 过滤默认值而丢失历史项。

### 4. 服务端兜底保护

即使前端已经做了预检查，`POST /api/runs` 仍需服务端兜底，避免双标签页或竞态造成重复提交。

新增规则：

- 当同一 ticker 仍存在 `queued` 或 `running` 记录时，`POST /api/runs` 返回 `409`。
- 返回 payload 或错误 detail 中应包含：
  - `active_run_id`
  - `active_run_status`
  - 适合前端展示的错误类型标识，例如 `ticker_active_run_exists`

这样前端即使错过预检查，也能回退到“正在分析中，是否立即查看”的阻断弹窗。

### 5. 同日同票完全独立

仅靠预检查弹窗还不足以实现“同日同票完全独立”。

当前 memory log 以 `(ticker, trade_date)` 作为 pending 写入幂等键，意味着同一股票同一天重复完成分析时，后续 run 可能共享或覆盖同一条 pending 记忆语义。

需要改为：

- memory log 写入与 deferred reflection 以 `run_id` 为主键。
- 同一 `ticker + trade_date` 的多次 run 各自写入独立记录。
- 反思补算时按 `run_id` 更新对应条目，而不是按 `(ticker, trade_date)` 匹配第一条 pending 记录。

目标结果：

- 同一天对同一股票启动多次分析时，每个 run 都拥有独立的历史记录和记忆条目。
- 不因“同日同票”而吞掉第二次及后续 run 的 memory pending 记录。

### 6. 分析前弹窗组件设计

新增一个前端组件：

- `frontend/src/components/runs/RunHistoryConfirmDialog.vue`

组件职责：

- 根据模式渲染两种弹窗：
  - `active`
  - `recent-history`
- 展示历史记录表格。
- 展示分页控制。
- 暴露行点击事件与主操作按钮事件。

表格列最小集合：

- `日期`
- `状态`
- `信号`

说明：

- 用户先前将“日志”列明确更正为“日期”，因此本次设计使用 `日期`。
- “模型供应商”不强制出现在该弹窗表格中，避免弹窗过宽；该信息在运行列表页补列展示。

交互要求：

- 点击行时立即路由跳转 `/runs/:runId`。
- 活动 run 阻断模式下，主按钮“立即查看”应跳活动 run。
- 近 3 天确认模式下，主按钮“启动新的分析”才真正继续创建 run。

### 7. 运行详情页停止分析

`RunDetailPage` 需要为活动 run 显示停止按钮。

显示条件：

- `status === "queued"` 或 `status === "running"`

行为：

- 调用现有 `POST /api/runs/{run_id}/cancel`
- 成功后刷新详情数据
- 将状态更新为取消后的最新状态

这样用户从分析页阻断弹窗点击“立即查看”进入详情页后，可以完成“查看并手动停掉当前分析”的闭环。

### 8. 运行列表页展示模型供应商

`RunsPage` 的公司分组卡片内，`recent_runs` 表格新增 `llm_provider` 列。

要求：

- 复用现有 `RunSummary.llm_provider`
- 无值时显示 `N/A` 或现有通用空值文案
- 不改变现有点击行进入详情页的交互

本次变更只要求展示，不要求新增按 provider 筛选 UI。

## 接口与数据结构调整

### 新增 Schema

后端新增一个 ticker-history 分页响应模型，字段：

- `ticker`
- `company_name`
- `latest_created_at`
- `has_active_run`
- `active_run_id`
- `active_run_status`
- `page`
- `page_size`
- `total_count`
- `items: list[RunSummary]`

### 复用现有 RunSummary

不重新定义历史记录明细结构，统一复用 `RunSummary`，避免：

- 同一条 run 摘要在多个接口中字段漂移
- 前端重复维护多个相近类型

### 取消接口

不新增新的停止接口，继续复用现有：

- `POST /api/runs/{run_id}/cancel`

## 错误处理

### 分析页预检查

- ticker 为空：维持现有前端校验，直接报错，不发预检查请求。
- ticker-history 请求失败：显示错误消息，不直接创建 run。

### 服务端兜底

- 当 `POST /api/runs` 命中同 ticker 活动 run 保护时，前端应优先按结构化错误处理，并弹出阻断弹窗。
- 若后端只返回文本错误，前端至少要能回退显示清晰错误提示，而不是误报“启动成功”。

### 跳转查看

- 若用户点击的历史记录不存在或已被删除，沿用现有 run detail 错误提示。

## 测试设计

### 后端测试

- ticker-history 接口按 ticker 过滤且分页正确。
- ticker-history 返回 `has_active_run` / `active_run_id` / `active_run_status`。
- ticker-history 结果按 `created_at desc` 排序。
- 同 ticker 存在 `queued` / `running` 时，`POST /api/runs` 返回 `409`。
- memory log 在同一 `ticker + trade_date` 多 run 场景下按 `run_id` 独立写入。

### AnalyzePage 前端测试

- 无历史时直接创建 run。
- 近 3 天有历史时弹确认弹窗，点击“启动新的分析”后才发起创建。
- 有活动 run 时弹阻断弹窗，且不会发起创建请求。
- 点击历史记录行跳转到 `/runs/:runId`。

### RunDetailPage 前端测试

- 活动 run 显示停止按钮。
- 点击停止按钮后调用取消接口并刷新状态。

### RunsPage 前端测试

- `recent_runs` 表格展示模型供应商列。
- 无 `llm_provider` 时显示空值占位。

## 风险与注意事项

### memory log 主键迁移风险

把 pending 记录从 `(ticker, trade_date)` 改为 `run_id` 主键会影响：

- 现有 log 解析
- deferred reflection 更新逻辑
- 旧记录兼容

需要保证：

- 历史老格式记录仍可读取
- 新格式优先走 `run_id`
- 不因迁移导致旧 reflection 永远无法补算

### 时间边界

“近 3 天”按浏览器本地自然日计算，必须避免：

- 服务器时区和前端时区不一致造成误判
- 用 UTC 日期直接切片导致中国/美国用户看到不同结果

### 页面复杂度

`AnalyzePage.vue` 已经较大，新的弹窗和预检查逻辑应尽量拆到独立组件与辅助函数中，避免继续堆积页面文件。

## 实施摘要

本次方案通过“ticker-history 专用接口 + 分析前弹窗预检查 + 服务端活动 run 兜底 + run_id 级 memory 独立化”实现以下结果：

- 同票近 3 天分析过时，用户必须先确认再重新分析。
- 同票仍在分析中时，用户不能重新分析，只能查看当前 run。
- 该股票全部历史记录可以在弹窗中按 `10` 条一页查看，并随时跳转详情页。
- 运行详情页可以手动停止活动 run。
- 运行列表页展示模型供应商。
- 同日同票多次分析在历史与 memory 语义上完全独立。
