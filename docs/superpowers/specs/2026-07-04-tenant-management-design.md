# Tenant 管理设计

## 背景

当前 Web 端已经有 `tenant` 这一层隔离语义：

- 用户记录带有 `tenant_id`。
- 运行状态、设置、工作区数据、checkpoint、memory 等都按 tenant 落盘。
- 登录态请求默认会被绑定回当前用户所属的 tenant。

但现状只支持“tenant 内管理”：

- `/api/admin/users` 只能管理当前管理员所在 tenant 的用户。
- 没有独立的 tenant 注册表。
- 没有 tenant 列表、tenant 详情、新建 tenant、禁用 tenant、删除 tenant 的后台管理能力。
- 现有 `/api/system/tenants` 更像运行时发现接口，不是正式的 tenant 管理入口。

这导致系统虽然已经具备多 tenant 数据隔离基础，却没有完整的 tenant 管理平面。

## 目标

- 为现有 `admin` 提供跨 tenant 的管理能力。
- 提供独立的 Tenant 管理页面，支持查看、创建、禁用、归档 tenant。
- 新建 tenant 时，同时创建该 tenant 的首个管理员用户。
- 支持在 tenant 详情页中直接管理该 tenant 下的用户。
- 保持现有普通用户和 tenant 内工作区行为不变。

## 非目标

- 不新增 `system admin` 或 `platform admin` 新角色。
- 不把整个前端工作区切换为“进入某个 tenant 运行”模式。
- 不做 tenant 数据的物理删除，不直接清理 run 文件、settings、memory、checkpoint 等磁盘内容。
- 不重构现有所有 tenant 感知接口，只对管理面新增明确入口。

## 当前约束

### 权限与登录态

- 现有中间件在 session 登录模式下，会把请求有效 tenant 固定为 `session_user.tenant_id`。
- 现有 `admin` 只是“当前 tenant 的管理员”，并没有跨 tenant 能力。
- 前端虽然已有 `tenantId` 的本地存储与传参能力，但在 session 登录场景下不会真正生效。

### 数据分布

- 用户和会话保存在 `auth.db`。
- tenant 级设置保存在 `~/.tradingagents/web/tenants/<tenant_id>/settings.json`。
- 运行记录、事件、checkpoint、memory 等也都散落在 tenant 目录下。

### 现有 UI

- 导航里只有 `Settings` 和 `Users` 两个 admin 入口。
- `UserManagementPage` 当前默认就是“当前 tenant 用户管理页”。

这些约束决定了第一版最稳的方案不是“全局切换 tenant 上下文”，而是新增独立的 tenant 管理平面。

## 核心设计

### 1. 权限模型

本次不引入新角色，直接让现有 `admin` 获得跨 tenant 管理能力，但仅限新增的 tenant 管理入口。

具体分层如下：

- 普通业务页继续遵循当前行为：
  - `viewer` / `analyst` / `admin` 仍然只操作自己所属 tenant 的工作区数据。
- 新增的 tenant 管理接口仅允许 `admin` 访问。
- `admin` 在 tenant 管理接口中可以查看所有 tenant，并对目标 tenant 做管理动作。

这样做的代价是：`admin` 的含义将从“tenant 内管理员”扩展为“全平台管理员”。这是有意的产品决策。

### 2. Tenant Registry

新增正式的 tenant 注册表，避免继续依赖“目录是否存在”来推断 tenant。

建议在 `auth.db` 中新增 `tenants` 表，字段至少包括：

- `id`: 主键，内部 UUID 或稳定字符串 ID。
- `tenant_id`: 唯一业务标识，沿用现有 tenant slug 语义。
- `display_name`: 展示名称。
- `disabled`: 是否禁用。
- `archived`: 是否归档。
- `created_at`
- `updated_at`

约束：

- `tenant_id` 继续复用现有 tenant slug 校验规则，只允许字母、数字、点、横线、下划线。
- `tenant_id` 全局唯一。
- tenant 一旦创建，`tenant_id` 不允许修改，避免路径迁移和历史数据错位。

### 3. Tenant 生命周期

#### 新建 tenant

新建 tenant 时必须同时提交：

- `tenant_id`
- `display_name`
- 首个管理员用户信息：
  - `username`
  - `email`
  - `display_name`
  - `password`

创建动作要么全部成功，要么全部失败，保证不会出现“tenant 已建但没有管理员”的半成品状态。

创建成功后：

- `tenants` 表新增记录。
- `users` 表新增该 tenant 的首个 `admin` 用户。
- 允许该 tenant 后续通过现有登录流程进入系统。

#### 禁用 tenant

禁用 tenant 后：

- 该 tenant 下所有用户禁止登录。
- 已登录会话访问受保护接口时应返回明确错误，提示 tenant 已禁用。
- tenant 历史数据和用户记录全部保留。

禁用是可逆操作，应支持重新启用。

#### 删除 tenant

第一版删除采用“逻辑删除 / 归档”：

- 将 `archived` 置为 `true`。
- 默认 tenant 列表不展示已归档 tenant，除非显式查看归档项。
- 已归档 tenant 不允许继续登录和写入新数据。
- 不物理删除 `auth.db` 中用户记录。
- 不物理删除 tenant 目录下的 settings、runs、memory、checkpoint 等文件。

这样可以避免高风险的文件系统级清理，并保留恢复空间。

### 4. 管理接口设计

新增一组显式的 tenant 管理接口，而不是复用业务工作区接口。

建议的接口分层：

#### Tenant 列表与详情

- `GET /api/admin/tenants`
  - 返回 tenant 列表。
  - 包含基础统计信息，例如用户数、活跃管理员数、是否禁用、是否归档。

- `POST /api/admin/tenants`
  - 创建 tenant 与首个 admin。

- `GET /api/admin/tenants/{tenant_id}`
  - 返回单个 tenant 详情。

- `PATCH /api/admin/tenants/{tenant_id}`
  - 允许更新 `display_name`、`disabled`、`archived`。

#### 跨 tenant 用户管理

不要继续让 `/api/admin/users` 只隐式依赖“当前登录用户所属 tenant”，而是新增显式的目标 tenant 路径：

- `GET /api/admin/tenants/{tenant_id}/users`
- `POST /api/admin/tenants/{tenant_id}/users`
- `PATCH /api/admin/tenants/{tenant_id}/users/{user_id}`
- `DELETE /api/admin/tenants/{tenant_id}/users/{user_id}`

这样接口语义清晰，也方便前端 tenant 详情页直接挂载用户管理。

现有 `/api/admin/users` 可以保留作为兼容入口，但建议内部逐步退化为“当前 tenant 用户页专用”。

### 5. 登录与授权行为调整

需要在 session 模式下增加 tenant 状态校验。

新增行为：

- 登录时，如果用户所属 tenant 被禁用或归档，直接拒绝登录。
- 已登录用户访问任意受保护接口时，如果所属 tenant 现已被禁用或归档，也应返回 403。

但不改变原有 tenant 绑定语义：

- 普通工作区请求依旧以 `current_user.tenant_id` 为准。
- 只有新增的 `/api/admin/tenants...` 管理接口允许 `admin` 跨 tenant 显式指定目标。

### 6. 前端信息架构

新增一个与 `Settings`、`Users` 同级的 admin 导航入口：

- `Tenants`

页面拆分建议：

#### TenantListPage

列表展示：

- `tenant_id`
- `display_name`
- 状态（active / disabled / archived）
- 用户数
- 管理员数
- 创建时间
- 操作按钮（查看、禁用/启用、归档）

页面顶部提供“新建 tenant”表单或弹层。

#### TenantDetailPage

展示：

- tenant 基础信息
- 状态切换
- 用户列表
- 新建 tenant 用户

这里的用户管理交互可以复用当前 `UserManagementPage` 的大部分逻辑，但数据源切换为显式 tenant 路由。

#### 现有 UserManagementPage

保留当前页面，继续作为“当前 tenant 用户管理页”。

这能降低迁移风险，也能保持当前已存在的使用习惯。

### 7. 数据与兼容策略

需要处理“旧系统没有 tenants 表”的情况。

启动或 schema 升级时：

- 自动创建 `tenants` 表。
- 从现有 `users` 表中扫描所有去重后的 `tenant_id`。
- 为每个已存在 tenant 自动补建一条 registry 记录：
  - `tenant_id = users.tenant_id`
  - `display_name = tenant_id`
  - `disabled = false`
  - `archived = false`

这样老数据可以平滑接入，不要求手工迁移。

## 错误处理

### Tenant 创建

- `tenant_id` 冲突返回 409。
- 首个 admin 的 `username` / `email` 冲突返回 409。
- 任一字段校验失败返回 400。

### Tenant 状态修改

- 不允许禁用或归档不存在的 tenant。
- 不允许删除默认不存在 registry 的幽灵 tenant；应先由迁移逻辑补齐。

### 用户管理

- 目标用户不属于目标 tenant 时返回 404，而不是泄露跨 tenant 信息。
- 若某 tenant 仅剩最后一个活跃 admin，则沿用现有“不能移除最后一个 admin”的约束。

## 测试

### 后端

- schema 测试：
  - 自动创建 `tenants` 表。
  - 旧用户数据可补建 tenant registry。

- 权限测试：
  - `admin` 可访问 tenant 管理接口。
  - `analyst` / `viewer` 不能访问 tenant 管理接口。

- 路由测试：
  - tenant 列表返回基础统计。
  - 可创建 tenant 与首个 admin。
  - 可禁用 / 启用 tenant。
  - 可归档 tenant。
  - tenant 详情页用户接口只返回目标 tenant 用户。

- 登录测试：
  - disabled tenant 用户无法登录。
  - archived tenant 用户无法登录。
  - tenant 被禁用后，已登录用户后续请求会被拒绝。

### 前端

- 路由与导航测试：
  - admin 可见 `Tenants` 导航。
  - 非 admin 不可见。

- 页面测试：
  - tenant 列表加载成功。
  - 新建 tenant 提交正确 payload。
  - tenant 状态切换按钮发起正确请求。
  - tenant 详情页能加载并管理目标 tenant 用户。

## 风险与约束

- 把 `admin` 直接提升为跨 tenant 管理员，会扩大既有权限语义；这是本次明确接受的产品取舍。
- tenant 逻辑删除后，底层文件仍保留，占用磁盘空间；这是为了换取更低的数据丢失风险。
- 现有 `tenantId` 前端上下文仍与真正的 session tenant 存在双轨语义；第一版不尝试统一为“全局 tenant 切换模式”。
- 如果后续确实需要“进入 tenant 工作区”体验，应基于本次 tenant registry 和显式管理接口另起一版设计。

