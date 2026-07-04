# 一次性分析任务与静态股票分组设计

## 背景

当前系统已经支持两类接近的能力：

- 关注列表 `watchlist`
- 循环自动化 `automations`，只支持 `daily/weekly` 和 `manual/watchlist`

新的产品目标不是扩展现有循环自动化的一个小字段，而是补齐两项独立能力：

1. 一次性计划分析任务
2. 工作区级、可复用的静态股票分组

其中一次性任务需要支持：

- 指定一次执行时间，精度到分钟
- 指定独立的 `analysis_date`
- 到点后批量入队分析
- 执行后保留在列表里
- 如果服务错过执行时间，不自动补跑，而是标记为 `missed`
- 在执行前允许编辑

股票来源需要同时支持：

- 手动个股选择
- 静态自定义分组
- 全部关注列表

并且来源不是单选，而是可以组合选择后取并集。

## 目标

- 新增一次性任务后端资源，不修改现有循环自动化的数据模型
- 新增静态股票分组后端资源，独立于关注列表
- 在自动化工作区里新增一次性任务创建与列表能力
- 在组合页中新增股票分组管理能力
- 一次性任务保存分析配置快照
- 一次性任务保存来源快照与最终解析后的股票集合快照
- 任务执行时使用保存下来的股票集合与分析配置，不受后续默认配置、关注列表或分组变化影响

## 非目标

- 不改造现有 `daily/weekly` 循环自动化的语义
- 不在本次实现中支持一次性任务自动补跑
- 不在本次实现中支持秒级调度
- 不在本次实现中把分组做成动态分组
- 不在本次实现中支持任务执行后再次编辑
- 不在本次实现中新增独立“股票分组页面”路由

## 方案概览

采用“独立资源、分页面职责”的方案：

- 保留现有 `automations` 作为循环自动化能力
- 新增 `one_time_analysis_tasks`
- 新增 `stock_groups`
- 在自动化页中新增一次性任务区域，负责创建、查看、编辑、取消一次性任务
- 在组合页中新增“股票分组”管理区域，负责分组的创建、编辑、删除

这样可以保持三类对象的边界清晰：

- `watchlist`：内置固定来源
- `stock_groups`：用户可维护的静态来源池
- `one_time_analysis_tasks`：一次性调度对象

## 数据模型

### 1. 股票分组 `stock_groups`

工作区级可复用静态分组。

建议字段：

- `id`
- `name`
- `tickers`
- `created_at`
- `updated_at`

约束：

- `name` 在当前工作区唯一
- `tickers` 保存时统一大写并去重
- 分组里的股票不要求来自关注列表
- 分组与关注列表互不联动

特殊规则：

- 关注列表本身不落成一条可编辑 `stock_group`
- 前后端都把“全部关注列表”视为内置来源

### 2. 一次性任务 `one_time_analysis_tasks`

建议字段：

- `id`
- `name`
- `status`
- `scheduled_for`
- `analysis_date`
- `selection_snapshot`
- `analysis_config`
- `created_at`
- `updated_at`
- `triggered_at`
- `completed_at`
- `last_error`
- `last_queued_count`
- `run_ids`

其中：

- `scheduled_for`：本地时间，精度到分钟
- `analysis_date`：与 `scheduled_for` 独立
- `analysis_config`：保存创建或最后一次编辑时的分析配置快照
- `selection_snapshot`：保存来源快照与最终股票集合快照

### 3. 来源快照 `selection_snapshot`

一次性任务不在执行时实时展开来源，而是在创建或编辑保存时就把来源解析成最终集合。

建议结构：

```json
{
  "manual_stocks": [
    {
      "market": "cn_a",
      "symbol": "600519.SH",
      "name": "贵州茅台",
      "exchange": "SSE"
    }
  ],
  "group_snapshots": [
    {
      "id": "group-1",
      "name": "AI Leaders",
      "tickers": ["NVDA", "MSFT"]
    }
  ],
  "include_watchlist": true,
  "watchlist_snapshot": ["AAPL", "0700.HK"],
  "resolved_tickers": ["600519.SH", "NVDA", "MSFT", "AAPL", "0700.HK"]
}
```

设计原则：

- `manual_stocks` 保留市场与展示信息，便于任务详情回显
- `group_snapshots` 保存分组名与当时的股票快照，避免后续分组修改影响历史任务
- `watchlist_snapshot` 保存选择任务时关注列表的股票快照
- `resolved_tickers` 是最终用于执行的股票集合

这意味着：

- 任务创建后，后续分组变化不会改写任务
- 任务创建后，后续关注列表变化不会改写任务
- 如果用户想使用最新关注列表或最新分组内容，需要在执行前重新编辑并保存任务

## 状态模型

`status` 取值建议为：

- `scheduled`
- `queued`
- `running`
- `completed`
- `missed`
- `cancelled`

状态流转规则：

1. 新建任务后为 `scheduled`
2. 到点且调度器在该分钟窗口内处理到任务：
   - 根据 `resolved_tickers` 批量创建分析 runs
   - 任务转为 `queued`
   - 记录 `triggered_at`、`last_queued_count`、`run_ids`
3. 相关 runs 全部结束后：
   - 任务转为 `completed`
   - 记录 `completed_at`
4. 如果调度器首次看到该任务时，当前时间已经超过计划分钟窗口：
   - 任务转为 `missed`
   - 不自动补跑
5. 用户在执行前手动取消：
   - 任务转为 `cancelled`

### 分钟窗口语义

由于任务精度只到分钟，因此调度判定按“分钟窗口”执行：

- 若 `scheduled_for = 2026-07-04 14:30`
- 调度器在 `14:30:00` 到 `14:30:59` 间处理到该任务，则应执行
- 若调度器恢复时已经是 `14:31` 及以后，则该任务标记为 `missed`

这样可以避免正常轮询延迟被误判为错过，同时满足“不自动补跑”的要求。

## 编辑与取消规则

仅 `scheduled` 状态允许编辑。

可编辑内容：

- 任务名称
- `scheduled_for`
- `analysis_date`
- 手动个股选择
- 分组选择
- 是否包含关注列表
- 分析配置快照

编辑后行为：

- 重新计算 `selection_snapshot`
- 重新计算 `resolved_tickers`
- 覆盖旧分析配置快照
- 更新时间 `updated_at`

`queued/running/completed/missed/cancelled` 均只读。

取消规则：

- 对 `scheduled` 任务提供“取消”操作
- 取消后进入 `cancelled`
- 本次实现不提供物理删除历史任务的能力

## 后端接口

### 股票分组接口

- `GET /api/stock-groups`
- `POST /api/stock-groups`
- `PATCH /api/stock-groups/{group_id}`
- `DELETE /api/stock-groups/{group_id}`

接口语义：

- `GET` 返回当前工作区所有静态分组
- `POST` 创建分组
- `PATCH` 修改分组名称或股票集合
- `DELETE` 删除分组

删除约束：

- 已经引用了该分组的历史任务不受影响，因为任务存的是快照
- 删除后只影响后续新建或编辑任务时的可选列表

### 一次性任务接口

- `GET /api/one-time-tasks`
- `POST /api/one-time-tasks`
- `PATCH /api/one-time-tasks/{task_id}`
- `POST /api/one-time-tasks/{task_id}/cancel`

建议 `GET` 支持的查询参数：

- `status`
- `page`
- `page_size`

建议 `POST/PATCH` payload 结构：

```json
{
  "name": "周五晚间观察篮子",
  "scheduled_for": "2026-07-10 21:30",
  "analysis_date": "2026-07-10",
  "manual_stocks": [
    {
      "market": "cn_a",
      "symbol": "600519.SH",
      "name": "贵州茅台",
      "exchange": "SSE"
    }
  ],
  "group_ids": ["group-1", "group-2"],
  "include_watchlist": true,
  "analysis_config": {
    "analysts": ["market", "news"],
    "llm_provider": "openai",
    "research_depth": 3,
    "output_language": "Chinese"
  }
}
```

服务端保存时需要：

1. 读取 `group_ids` 对应的当前分组内容
2. 如果 `include_watchlist = true`，读取当前关注列表内容
3. 与 `manual_stocks` 合并，去重出 `resolved_tickers`
4. 将快照一并保存进任务

## 调度与执行

### 调度入口

在现有 worker 轮询中新增一次性任务处理逻辑，与循环自动化并行。

建议顺序：

1. 处理待恢复 runs
2. 处理循环自动化
3. 处理一次性任务
4. 处理 webhook 通知
5. 处理 queued runs

### 一次性任务调度规则

每轮轮询读取当前工作区的 `scheduled` 任务：

- 若 `scheduled_for` 所在分钟等于当前分钟，执行入队
- 若 `scheduled_for` 所在分钟早于当前分钟，标记 `missed`
- 若 `scheduled_for` 晚于当前分钟，跳过

### 入队方式

一次性任务执行时不再展开来源，而是直接遍历 `selection_snapshot.resolved_tickers`。

对每个 ticker：

- 构造 `AnalysisRequest`
- 使用任务内保存的 `analysis_config`
- 使用任务内保存的 `analysis_date`
- 批量创建 runs

这样可以保证：

- 任务执行结果与创建时预览一致
- 不受执行前其他配置变更影响

## 前端设计

## 页面职责拆分

### 自动化页

自动化页继续作为“调度相关能力”的入口，但分成两块：

- `Recurring Automations`
- `One-Time Tasks`

本次重点新增 `One-Time Tasks` 区域。

### 组合页

组合页新增 `Stock Groups` 管理区域。

该区域负责：

- 创建静态分组
- 编辑静态分组
- 删除静态分组

一次性任务页只引用这里已经存在的分组，不承担分组 CRUD。

## 一次性任务创建器布局

任务创建区使用上下布局，不使用左右并列来源选择。

页面结构：

1. 基础信息
2. 个股选择
3. 分组与关注列表选择
4. 最终股票集合
5. 分析配置

### 1. 基础信息

字段：

- 任务名称
- 计划执行时间 `YYYY-MM-DD HH:MM`
- `analysis_date`

### 2. 个股选择

交互规则：

- 用户先选择市场
- 市场支持：
  - A 股
  - 港股
  - 美股
- 选择市场后，加载该市场股票下拉列表
- 股票下拉采用多选
- 切换市场不会清空之前已选股票
- 已选股票以 chips 持续展示，可单独删除

这里的本质是“累积式多市场个股选择”。

### 3. 分组与关注列表选择

交互规则：

- 通过分组列表选择已有分组，支持多选
- 分组选择结果以 chips 展示，可单独删除
- 同区块提供一个独立开关：
  - `包含全部关注列表`

也就是说，这里不是单选来源，而是组合来源构建器的一部分。

### 4. 最终股票集合

该区块实时展示：

- 手动个股
- 选中分组展开后的股票
- 关注列表股票

三者取并集后的去重结果。

展示内容：

- ticker chips
- 总数
- 可单独移除某一 ticker

这里展示的集合就是最终会被保存进任务快照并用于执行的集合。

### 5. 分析配置

沿用现有分析配置字段，但在保存任务时作为快照落库。

## 一次性任务列表

任务列表建议按状态分组展示：

- `Scheduled`
- `Completed`
- `Missed`
- `Cancelled`

每张任务卡展示：

- 任务名称
- 计划执行时间
- `analysis_date`
- 来源摘要
- 最终股票数量
- 状态

操作规则：

- `Scheduled`：可编辑、可取消
- `Completed`：只读，可查看关联 runs
- `Missed`：只读，明确标记错过
- `Cancelled`：只读

## 组合页中的股票分组管理

组合页新增一个 `Stock Groups` 区块，保持与当前 `watchlist / portfolio / alerts / screener` 的 card 式结构一致，而不是新开独立路由。

原因：

- 更贴合当前 `PortfolioPage.vue` 的已有页面模式
- 改动范围更可控
- 用户能在同一资产维护页里管理 watchlist、portfolio 和 groups

该区块包含：

- 创建分组表单
- 分组列表
- 单个分组的 ticker 编辑区
- 删除操作

## 校验与错误处理

### 股票分组

- 分组名称不能为空
- 分组名称在当前工作区必须唯一
- 分组至少包含一个 ticker

### 一次性任务

- 任务名称不能为空
- `scheduled_for` 必须符合 `YYYY-MM-DD HH:MM`
- `analysis_date` 必须符合 `YYYY-MM-DD`
- 最终 `resolved_tickers` 不能为空
- 只有 `scheduled` 状态允许编辑或取消

### 调度执行

- 如果某个 ticker 创建 run 失败，需要记录 `last_error`
- 若部分 ticker 入队成功，不回滚整个任务，仍进入 `queued`
- 任务完成状态以 runs 生命周期为准，不单独引入 `partial_failed`

## 测试

### 后端

- schema 测试：一次性任务时间格式校验
- schema 测试：分组名称与 ticker 去重逻辑
- 路由测试：分组 CRUD
- 路由测试：创建任务时正确展开分组与关注列表并生成 `resolved_tickers`
- 路由测试：编辑 `scheduled` 任务会重建快照
- 路由测试：非 `scheduled` 任务不可编辑
- worker 测试：在计划分钟内执行任务并批量入队
- worker 测试：超过计划分钟后标记 `missed`
- worker 测试：执行使用的是任务快照而不是当前分组或当前关注列表

### 前端

- 自动化页测试：存在一次性任务区域
- 任务创建器测试：市场切换不清空已选个股
- 任务创建器测试：个股下拉支持多选
- 任务创建器测试：分组列表支持多选
- 任务创建器测试：勾选关注列表后最终集合正确并集去重
- 任务创建器测试：最终集合可展示和删除 ticker chip
- 组合页测试：股票分组 card 能创建、编辑、删除分组

## 风险与约束

- 一次性任务与循环自动化都会进入同一个 run 队列，队列拥堵时任务只是“按时入队”，不保证“按时完成”
- 股票分组与关注列表都可能很大，前端多选控件需要注意性能与搜索体验
- 由于任务保存了来源快照，用户如果后续修改分组但忘记同步编辑任务，任务执行结果会与当前分组不一致；这是刻意选择的稳定性优先语义
- 本次先把分组管理放进组合页 card 区块；如果后续资产维护页继续变重，再考虑拆成更独立的信息架构

## 结论

本方案把“一次性调度对象”和“静态股票来源池”拆成独立资源：

- `one_time_analysis_tasks` 解决一次性计划执行
- `stock_groups` 解决可复用的静态股票集合

同时明确采用以下关键语义：

- 任务来源是组合式选择，而不是单选来源
- 个股选择与分组选择采用上下布局
- 任务页只做来源选择
- 分组 CRUD 放在组合页
- 任务执行使用保存时的快照
- 超时不补跑，只标记 `missed`

这组语义与当前产品目标一致，也最容易在现有代码结构中稳定落地。
