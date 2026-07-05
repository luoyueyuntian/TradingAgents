# 组合资产模块拆分与独立页面设计

## 背景

当前 `/portfolio` 页面把以下能力堆叠在一个页面中：

- `watchlist`
- `portfolio positions`
- `stock groups`
- `alerts`
- `screener`

其中前四块都属于“资产维护”能力，但目前存在几个问题：

1. 页面职责过重，用户在一个长页面里维护多种不同对象，切换成本高
2. 各模块的 CRUD 交互不一致，大部分仍是内联录入，缺少统一的新增/编辑体验
3. 股票选择体验没有复用分析页已经成熟的“市场切换 + 股票搜索”模式
4. 前端结构集中在单个 `PortfolioPage.vue` 中，后续继续扩展会变得更难维护

新的产品目标不是重做整个资产体系，而是在尽量复用现有租户级数据模型的前提下，把前四块拆成独立模块页面，并统一 CRUD 交互。

## 目标

- 保留左侧导航中的单个 `组合` 入口
- 保留 `/portfolio` 作为资产管理首页
- 将 `watchlist / positions / stock groups / alerts` 拆成 4 个独立子页面
- 每个子页面都支持符合本次范围的 CRUD
- `新增` 和 `编辑` 统一使用弹窗
- 弹窗中的股票选择方式与分析页一致，复用“市场 + 搜索 + 选择”体验
- 保持当前按 `tenant_id` 隔离的数据模型，不改成按 `user_id` 隔离
- 尽量复用现有股票搜索与租户存储能力，避免引入数据迁移

## 非目标

- 不改造现有左侧主导航为 4 个一级菜单
- 不把这批数据改成按用户隔离
- 不把 `watchlist` 的“编辑”定义为替换成另一只股票
- 不在本次实现中改造 `screener` 为独立子页面
- 不在本次实现中改变 `stock groups` 的租户级共享语义
- 不在本次实现中重做分析页或自动化页已有的选股业务逻辑

## 已确认的产品决策

### 1. 导航与入口

- 左侧主导航继续只保留一个 `组合`
- `/portfolio` 保留为资产管理首页
- 4 个模块通过 `/portfolio` 下的二级导航或 Tab 进入，而不是左侧新增 4 个一级菜单

### 2. CRUD 粒度

- 本次采用“单条 CRUD”
- `watchlist / positions / alerts` 每次新增 1 条
- `stock groups` 每次维护 1 个分组，但一个分组内可以选择多只股票

### 3. `watchlist` 的“编辑”定义

- `watchlist` 不做真正编辑
- 若用户想更换股票，使用“删除后重新新增”

### 4. 数据隔离边界

- 继续按 `tenant_id` 隔离
- 同一租户下共享这批资产数据
- 不新增 `user_id` 维度的读写隔离

## 方案概览

采用“保留组合首页 + 拆分子路由 + 共享弹窗与选股组件”的方案：

- `/portfolio` 从“单页承载所有维护动作”改为“资产管理首页”
- 新增 4 个 `/portfolio/*` 子路由页面
- 通过共享的页面壳层、二级导航和股票选择表单段，统一页面结构与交互
- 后端保持租户级存储结构，仅为 `positions` 和 `alerts` 补充缺失的更新接口
- `watchlist` 继续只支持查、新增、删除
- `stock groups` 继续复用现有完整 CRUD 能力

这样可以同时满足：

- 独立页面展示
- 左侧导航不膨胀
- 尽量少改后端
- 最大化复用分析页已有选股体验

## 信息架构与路由

### 路由结构

建议将当前单一路由：

- `/portfolio`

扩展为以下结构：

- `/portfolio`
- `/portfolio/watchlist`
- `/portfolio/positions`
- `/portfolio/stock-groups`
- `/portfolio/alerts`

推荐使用一个父级壳层组件承载 `/portfolio` 及其子路由，而不是让 5 个页面各自复制页头和子导航。

### 页面职责

#### 1. `/portfolio`

资产管理首页，负责：

- 展示四个模块入口卡片
- 展示摘要计数，例如：
  - watchlist 数量
  - positions 数量
  - stock groups 数量
  - alert rules 数量
- 提供进入 4 个子页面的显式入口
- 保留 `screener` 作为工具型区域，避免这次拆分导致现有第五块能力直接消失

首页不再承载前四个模块的 CRUD 表单。

#### 2. `/portfolio/watchlist`

独立的 watchlist 列表页，负责：

- 列出已保存股票
- 查看每只股票的最新状态/信号/名称等摘要
- 新增 1 只股票
- 删除 1 只股票

不提供编辑。

#### 3. `/portfolio/positions`

独立的持仓列表页，负责：

- 列出持仓记录
- 新增持仓
- 编辑持仓的数量和成本
- 删除持仓

#### 4. `/portfolio/stock-groups`

独立的股票分组页，负责：

- 列出分组
- 新增分组
- 编辑分组名称和分组内股票集合
- 删除分组

#### 5. `/portfolio/alerts`

独立的提醒规则页，负责：

- 列出提醒规则
- 新增提醒规则
- 编辑提醒规则的字段和值
- 删除提醒规则

## 数据隔离与作用域

### 保持租户级隔离

本次实现继续遵循当前 Web 工作区的租户级数据边界：

- 读写上下文由当前请求解析出的 `tenant_id` 决定
- `watchlist / positions / stock groups / alerts` 继续落在当前租户配置空间中
- 同租户用户共享这批数据
- 不新增 `user_id` 级字段、命名空间或迁移逻辑

### 这样做的原因

- 符合当前系统已有的工作区共享模型
- 避免把本次“页面拆分”扩展成“数据模型重构”
- 避免旧数据迁移与兼容风险
- 能让现有自动化、工作区摘要、导入导出逻辑继续复用当前数据

## 后端接口设计

### 保留的现有接口

#### Watchlist

- `GET /api/watchlist`
- `POST /api/watchlist`
- `DELETE /api/watchlist/{ticker}`

本次不新增 `watchlist` 更新接口。

#### Portfolio

- `GET /api/portfolio`
- `POST /api/portfolio/positions`
- `DELETE /api/portfolio/positions/{position_id}`

#### Alerts

- `GET /api/alerts`
- `POST /api/alerts/rules`
- `DELETE /api/alerts/rules/{rule_id}`

#### Stock Groups

- `GET /api/stock-groups`
- `POST /api/stock-groups`
- `PATCH /api/stock-groups/{group_id}`
- `DELETE /api/stock-groups/{group_id}`

### 新增接口

#### 1. 更新持仓

新增：

- `PATCH /api/portfolio/positions/{position_id}`

建议请求体：

```json
{
  "quantity": 12,
  "average_cost": 185.5
}
```

规则：

- 仅允许更新 `quantity` 和 `average_cost`
- 不允许通过该接口修改 `ticker`
- 若记录不存在，返回 `404`
- 若值非法，例如数量小于等于 0，返回 `400`

#### 2. 更新提醒规则

新增：

- `PATCH /api/alerts/rules/{rule_id}`

建议请求体：

```json
{
  "field": "status",
  "value": "failed"
}
```

规则：

- 仅允许更新 `field` 和 `value`
- 不允许通过该接口修改 `ticker`
- `value` 继续走现有规范化逻辑
- 若记录不存在，返回 `404`

### `GET /api/portfolio` 的定位

虽然模块被拆分，但 `GET /api/portfolio` 仍然保留并继续承担两类职责：

- 给 `/portfolio` 首页提供摘要与持仓概览
- 给工作区其他依赖投资组合摘要的页面继续复用

四个子页不需要都依赖这个大接口：

- `watchlist` 子页使用 `/api/watchlist`
- `positions` 子页使用 `/api/portfolio`
- `stock groups` 子页使用 `/api/stock-groups`
- `alerts` 子页使用 `/api/alerts`

## 前端页面与组件拆分

### 页面壳层

建议新增一个组合域壳层，例如：

- `PortfolioShellPage.vue`

职责：

- 承载 `PageHeader`
- 承载二级导航 / Tabs
- 提供子路由容器
- 负责共享的页面级提示信息样式

### 页面拆分建议

- `PortfolioHomePage.vue`
- `PortfolioWatchlistPage.vue`
- `PortfolioPositionsPage.vue`
- `PortfolioStockGroupsPage.vue`
- `PortfolioAlertsPage.vue`

当前 `PortfolioPage.vue` 将不再继续承担全部职责，避免它再次膨胀成一个超级页面。

### 共享组件建议

#### 1. 组合子导航

- `PortfolioSubnav.vue`

职责：

- 渲染 `首页 / Watchlist / Positions / Stock Groups / Alerts`
- 与当前子路由同步高亮
- 保持二级导航在资产管理域内一致

#### 2. 股票选择表单段

- `StockPickerField.vue` 或 `PortfolioStockPicker.vue`

职责：

- 复用分析页选股交互
- 支持：
  - 选择市场
  - 搜索股票
  - 显示候选项
  - 回填所选股票

底层复用：

- `/api/stocks/markets`
- 股票搜索接口
- `analyzeStockSelection` 中已有的市场映射、结果归一化等能力

#### 3. 弹窗壳层

- `EntityDialog.vue`

职责：

- 统一标题、按钮、错误提示、loading 状态
- 统一新增与编辑的弹窗布局

#### 4. 具体弹窗

- `WatchlistCreateDialog.vue`
- `PositionDialog.vue`
- `StockGroupDialog.vue`
- `AlertDialog.vue`

## 交互设计

### 统一原则

- `新增` 和 `编辑` 统一使用弹窗
- 列表页不做内联编辑
- 每个子页顶部展示：
  - 页面标题
  - 摘要计数
  - `新增` 按钮
- 列表项右侧提供 `编辑 / 删除`

### 1. Watchlist

#### 新增

- 打开新增弹窗
- 先选择市场
- 再按分析页方式搜索并选择 1 只股票
- 保存后加入 watchlist

#### 删除

- 在列表中直接删除

#### 编辑

- 本次不提供
- 如果用户想替换股票，采用“删除后重新新增”

### 2. Positions

#### 新增

- 弹窗中先选择 1 只股票
- 填写：
  - `quantity`
  - `average_cost`

#### 编辑

- 允许修改：
  - `quantity`
  - `average_cost`
- 默认不允许修改股票本身

#### 删除

- 在列表中直接删除

### 3. Stock Groups

#### 新增/编辑

- 输入分组名
- 在弹窗内使用分析页同款股票搜索能力，逐个将股票加入“已选列表”
- 不再以逗号分隔 ticker 文本框作为主交互
- 已选股票以 chips 或列表形式展示，可单独移除

#### 删除

- 在列表中直接删除分组

### 4. Alerts

#### 新增

- 选择 1 只股票
- 选择字段：
  - `signal`
  - `status`
- 输入值

#### 编辑

- 允许修改：
  - `field`
  - `value`
- 默认不允许修改股票本身

#### 删除

- 在列表中直接删除

## Screener 的处理

本次用户只要求把前四块拆成独立模块，未要求把 `screener` 一并拆成子页面。

因此建议：

- 不新增 `/portfolio/screener`
- `screener` 留在 `/portfolio` 首页
- 作为工具型区域继续使用

这样可以：

- 满足“前四块独立页面”的要求
- 避免本次无必要扩大范围
- 避免让原有能力突然消失

## 状态与数据加载

### 页面级加载

各子页各自请求所需资源，不共享一个大而全的 `loadAll()`：

- watchlist 页加载 `/api/watchlist`
- positions 页加载 `/api/portfolio`
- stock groups 页加载 `/api/stock-groups`
- alerts 页加载 `/api/alerts`

### 保存后的刷新策略

保存成功后：

- 关闭弹窗
- 刷新当前页面数据
- 可显示统一成功提示

删除成功后：

- 直接刷新当前列表
- 或在本地乐观移除后再与后端同步

优先建议使用“请求成功后重新拉当前模块数据”的保守策略，降低状态同步复杂度。

## 错误处理

- 弹窗内先做前端基础校验
- 必填项缺失时，不关闭弹窗，直接提示
- 提交过程中按钮进入 `loading`，避免重复提交
- 后端 `400` 错误显示在弹窗中
- 后端 `404` 说明记录已失效或被删除：
  - 关闭弹窗
  - 刷新当前列表
  - 提示用户数据已更新
- 股票搜索失败时，不清空已填写内容，只提示可重试
- 列表页加载失败时，沿用现有页面级错误消息模式

## 兼容性与迁移

### 数据迁移

本次不需要数据迁移。

原因：

- 仍使用当前租户级存储
- 仍使用现有对象结构
- 仅补充 `positions` 和 `alerts` 的更新接口

### 对现有功能的影响

- `/portfolio` 入口保留
- 原有 `watchlist / positions / alerts / stock groups` 数据直接在新页面里可见
- 现有工作区、自动化、摘要能力继续使用同一批租户数据
- 分析页和自动化页已有选股逻辑应被抽取复用，而不是被替换成另一套行为

## 测试策略

### 后端

- `PATCH /api/portfolio/positions/{position_id}`：
  - 成功更新数量和成本
  - 非法数量返回 `400`
  - 不存在记录返回 `404`
- `PATCH /api/alerts/rules/{rule_id}`：
  - 成功更新字段和值
  - 非法字段或值返回 `400`
  - 不存在记录返回 `404`
- 回归确认租户隔离未被破坏

### 前端

- 路由测试：
  - `/portfolio`
  - `/portfolio/watchlist`
  - `/portfolio/positions`
  - `/portfolio/stock-groups`
  - `/portfolio/alerts`
- 导航测试：
  - 左侧主导航仍只有一个 `组合`
  - 组合域内存在二级导航
- 首页测试：
  - 4 个入口卡片与摘要计数正确
  - `screener` 仍可见
- 子页测试：
  - 加载列表
  - 打开新增弹窗
  - 保存成功
  - 编辑成功（适用于 positions / stock groups / alerts）
  - 删除成功
- 股票选择组件测试：
  - 市场切换
  - 搜索建议
  - 选择后回填
- 权限测试：
  - `canWrite = false` 时新增/编辑/删除不可用或隐藏

### 回归

- 分析页选股行为不被破坏
- 自动化页的手动选股与股票分组能力不被破坏
- 现有 stock groups CRUD 回归保持通过

## 风险与控制

### 风险 1：共享选股组件抽取时破坏分析页

控制：

- 只抽取成熟的底层逻辑与展示片段
- 保留分析页自身业务流程不变
- 为分析页现有选股行为保留测试

### 风险 2：页面拆分后 `/portfolio` 首页能力缩水

控制：

- 首页保留摘要卡片与 `screener`
- 首页仍然是有效入口，不只是跳板空壳

### 风险 3：后端更新接口引入与现有 schema 不一致

控制：

- 为 `positions` 和 `alerts` 单独定义更新请求模型
- 不复用 create schema 强行兼容不同语义

## 最终方案

采用以下最终方案：

- 保留 `/portfolio` 作为资产管理首页
- 通过 `/portfolio/*` 子路由拆分 `watchlist / positions / stock groups / alerts`
- 左侧主导航仍只保留一个 `组合`
- 4 个子页通过二级导航或 Tab 进入
- `新增/编辑` 统一使用弹窗
- 弹窗中的股票选择复用分析页同款市场与搜索能力
- `watchlist` 只支持查、新增、删除
- `positions` 与 `alerts` 新增后端 `PATCH` 接口补齐编辑能力
- 继续保持按租户隔离，不改成按用户隔离
- `screener` 保留在 `/portfolio` 首页，不纳入本次独立子页面拆分
