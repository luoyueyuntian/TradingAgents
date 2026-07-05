# 当前租户用户管理 CRUD 设计

## 背景

当前 Web 端已经具备基础的用户管理能力，但交互形态仍然偏原型化：

- `/users` 页面以表格内联编辑为主，缺少标准的搜索区、操作栏、弹窗表单和批量操作。
- 删除语义复用了 `disabled`，并不是真正独立的软删除。
- 重置密码依赖管理员手动输入新密码，不符合“确认后自动生成并展示新密码”的管理体验。
- 登录只依赖 `identifier`，这意味着用户名和邮箱必须全局唯一，无法支持“同租户内唯一、跨租户可重复”。

同时，这次任务的范围已经明确收敛：

- 只改“当前登录用户所属 tenant”的 `/users` 管理页。
- 一起改登录页与登录接口，使登录时必须输入租户名称。
- 不改 `TenantDetailPage`，也不合并该页在其他任务中的进行中改动。

## 目标

- 将 `/users` 改造成标准的通用 CRUD 管理页。
- 支持顶部搜索过滤、操作栏、批量删除、弹窗新增/编辑、二次确认删除、二次确认重置密码。
- 将删除语义升级为真正的软删除，并为未来回收站预留后端接口。
- 将用户名和邮箱的唯一性改为“同租户内唯一”，且已软删除用户仍参与重复校验。
- 改造登录链路，使登录按 `tenant_id + identifier + password` 完成认证。
- 保持当前“用户管理仅管理当前登录用户所属 tenant 的用户”这一权限边界不变。

## 非目标

- 不改 `TenantDetailPage` 的 UI、数据源或交互。
- 不在本次任务中新增回收站入口。
- 不在本次任务中支持恢复已删除用户的前端流程。
- 不做跨 tenant 的普通用户管理。
- 不新增新的角色类型或权限模型。

## 当前约束

### 权限边界

- `/api/admin/users` 当前只管理当前登录管理员所属 tenant 的用户。
- 用户要求这一边界保持不变，不能扩展为跨 tenant 普通用户管理。

### 现有数据语义

- `users` 表当前有 `disabled`，但没有独立的 `deleted_at`。
- 删除用户时实际只是把 `disabled = 1`，这会和“账号禁用”语义混淆。
- 用户名和邮箱当前是全局唯一。

### 登录现状

- 现有 `/api/auth/login` 只接受 `identifier` 和 `password`。
- 现有登录页只输入“用户名/邮箱 + 密码”。
- 一旦将唯一性改为“同租户内唯一”，登录必须增加 `tenant_id` 作为定位条件。

## 核心设计

### 1. 页面架构

本次不把用户页做成“任意实体 schema 驱动”的后台框架，而是把现有 `AdminUserDirectory` 升级为“用户域内可复用的 CRUD 壳子”。

建议拆分如下：

- `UserManagementPage`
  - 负责页头、刷新动作和挂载共享用户 CRUD 组件。
- `UserCrudManager`（新共享组件，名称可在实现时调整）
  - 负责搜索区、操作栏、表格区、分页或空态、弹窗、确认框、结果框。
- `UserFormDialog`
  - 负责新增/编辑表单。
- `PasswordResultDialog`
  - 负责展示系统生成的临时密码并支持复制。

这保证：

- `/users` 页面本身保持轻量。
- 后续如果还需要“管理员专用用户视图”或“回收站视图”，可以复用同一套用户 CRUD 壳子。
- 不会把抽象过早推到整套后台框架级别。

### 2. `/users` 页面交互

页面结构固定为三段：

#### 顶部搜索过滤区

支持以下条件：

- `名称`
  - 输入框
  - 模糊匹配
  - 同时匹配 `username` 与 `display_name`
- `邮箱`
  - 输入框
  - 精确匹配
- `角色`
  - 下拉框
  - 选项：`admin` / `analyst` / `viewer`
- `状态`
  - 下拉框
  - 选项：`all` / `active` / `disabled` / `expired`

交互建议：

- 提供 `搜索` 和 `重置` 两个动作。
- 搜索条件变化后不自动请求，由显式点击搜索触发，避免无谓请求抖动。
- `重置` 会清空全部筛选条件并重新加载默认列表。

#### 操作栏

支持两个动作：

- `新增`
- `批量删除`

批量删除仅在勾选了至少一条记录时可用。

#### 表格区

列固定为：

- 用户名
- 显示名
- 角色
- 创建时间
- 到期时间
- 状态
- 操作

行操作固定为：

- 编辑
- 删除
- 重置密码

状态展示规则：

- `deleted_at` 不为空的记录默认不会出现在该页，所以不展示 `deleted`
- `disabled = true` 展示为 `disabled`
- `expires_at` 已过期且未删除时展示为 `expired`
- 其余展示为 `active`

状态管理规则：

- 用户仍需能在 `/users` 页完成“禁用/启用”。
- 为了不偏离你最初定义的操作列，本次不把“禁用/启用”加成新的主操作按钮。
- 建议在“状态”列提供状态标签或开关：
  - 当前为 `active` 时，可执行禁用
  - 当前为 `disabled` 时，可执行启用
  - 当前为 `expired` 时，只展示状态，不提供启用/禁用切换
- 禁用或启用建议带轻量确认，避免误触。

### 3. 新增与编辑表单

新增与编辑复用同一个弹窗表单。

表单项：

- 用户名
- 显示名
- 邮箱
- 角色
- 到期时间

规则：

- 新增时，以上字段均可编辑。
- 编辑时：
  - 用户名只读，不允许修改。
  - 显示名、邮箱、角色、到期时间允许修改。
- 到期时间允许为空，表示长期有效。

本次不在新增表单中让管理员手动输入初始密码。

新增成功后：

- 后端自动生成临时密码。
- 前端弹出结果框展示该密码。
- 用户被标记为 `must_change_password = true`。

### 4. 删除与软删除

删除必须二次确认。

后端删除语义改为真正的软删除：

- 为 `users` 表新增 `deleted_at` 字段。
- 删除时写入 `deleted_at` 与 `updated_at`。
- 同时删除该用户现有 session。
- 默认列表只返回 `deleted_at IS NULL` 的记录。

保留 `disabled` 作为“账号禁用”语义，不再让删除与禁用共用一个字段。

这次前端不展示回收站入口，但后端需预留能力：

- 列表支持显式查看已删除数据。
- 后续可新增恢复接口而无需重构删除模型。

### 5. 重置密码

重置密码必须二次确认。

确认后：

- 后端自动生成强密码。
- 更新目标用户密码哈希和盐。
- 删除目标用户现有 session。
- 将 `must_change_password` 置为 `true`。
- 响应中返回新生成的临时密码。

前端在请求成功后：

- 弹出结果框显示新密码。
- 提供复制按钮。
- 明确提示“请尽快交付给用户，用户首次登录后需修改密码”。

### 6. 数据模型调整

`users` 表建议新增：

- `deleted_at INTEGER NULL`

用户唯一性改为 tenant 级：

- `tenant_id + lower(username)` 唯一
- `tenant_id + lower(email)` 唯一

并且该唯一性对已软删除用户仍然生效。

这意味着：

- 删除用户不会释放用户名或邮箱。
- 同 tenant 下不能复用已删除用户的用户名或邮箱。
- 不同 tenant 下允许出现相同用户名或相同邮箱。

### 7. 登录链路调整

为了支持跨 tenant 重名账号，登录必须带上租户名称。

登录页改为 3 个字段：

- 租户名称
- 用户名或邮箱
- 密码

接口改为：

- `POST /api/auth/login`
- body: `{ tenant_id, identifier, password }`

后端认证逻辑改为：

1. 先校验并归一化 `tenant_id`
2. 在该 tenant 范围内查找 `identifier`
3. 校验密码
4. 校验用户状态与 tenant 状态
5. 创建 session

这样可以支持：

- 不同 tenant 复用同一个用户名
- 不同 tenant 复用同一个邮箱

同时不改变登录后的 tenant 绑定语义：

- 登录后所有普通工作区请求仍然绑定到该用户所属 tenant
- `/users` 仍然只操作当前登录用户所属 tenant 的用户

### 8. 后端接口设计

#### 用户列表

- `GET /api/admin/users`

查询参数：

- `name`
- `email`
- `role`
- `status`
- `deleted_scope`

约定：

- `name`：模糊匹配 `username` / `display_name`
- `email`：精确匹配
- `role`：精确匹配
- `status`：`all | active | disabled | expired`
- `deleted_scope`：`active | deleted | all`

本次前端默认固定请求 `deleted_scope=active`。

#### 新增用户

- `POST /api/admin/users`

请求体：

```json
{
  "username": "alice",
  "display_name": "Alice",
  "email": "alice@example.com",
  "role": "analyst",
  "expires_at": 1780000000000
}
```

响应体：

```json
{
  "user": {},
  "temporary_password": "generated-password"
}
```

#### 编辑用户

- `PATCH /api/admin/users/{user_id}`

允许字段：

- `display_name`
- `email`
- `role`
- `expires_at`
- `disabled`

不允许更新：

- `username`
- `tenant_id`

#### 删除用户

- `DELETE /api/admin/users/{user_id}`

语义：

- 软删除
- 返回删除后的 `user`

#### 批量删除

- `POST /api/admin/users/bulk-delete`

请求体：

```json
{
  "user_ids": ["u1", "u2", "u3"]
}
```

响应建议：

```json
{
  "deleted_ids": ["u1", "u2"],
  "failed": [
    {
      "user_id": "u3",
      "detail": "Cannot remove the last active admin from tenant"
    }
  ]
}
```

这样前端可以给出“部分成功”的明确反馈。

#### 重置密码

- `POST /api/admin/users/{user_id}/reset-password`

响应体：

```json
{
  "user": {},
  "temporary_password": "generated-password"
}
```

#### 回收站预留接口

本次至少预留以下能力之一：

- 通过 `deleted_scope=deleted|all` 查看已删除用户
- 后续可补 `POST /api/admin/users/{user_id}/restore`

前端本次不展示入口。

## 错误处理

### 表单与唯一性

- 同 tenant 用户名冲突：返回 `409`
- 同 tenant 邮箱冲突：返回 `409`
- 已删除用户占用用户名或邮箱时，仍返回 `409`
- 非法角色或非法时间格式：返回 `400`

### 删除

- 目标用户不存在：返回 `404`
- 试图删除最后一个活跃 admin：返回 `400`

### 禁用与启用

- 目标用户不存在：返回 `404`
- 试图禁用最后一个活跃 admin：返回 `400`
- 已软删除用户不允许再执行禁用或启用：返回 `400` 或 `404`，实现上保持一致

### 重置密码

- 目标用户不存在：返回 `404`
- 目标用户已删除：返回 `400` 或 `404`，实现上应保持一致

### 登录

- `tenant_id` 缺失：返回 `400`
- 指定 tenant 下不存在该账号或密码错误：统一返回 `401 Invalid credentials`
- 用户禁用：返回 `403`
- 用户过期：返回 `403`
- tenant 禁用或归档：返回 `403`

## 迁移策略

### 数据迁移

启动或 schema 升级时：

- 为 `users` 表补 `deleted_at`
- 新增 tenant 级大小写不敏感唯一索引：
  - `tenant_id + lower(username)`
  - `tenant_id + lower(email)`
- 移除或废弃全局唯一约束

如果历史数据已经存在跨 tenant 冲突风险较低，可直接迁移。
若迁移时发现现存脏数据，应在迁移阶段失败并输出明确错误，避免静默覆盖。

### 登录迁移

- 登录页前端改造与后端接口改造需要同一版本一起上线。
- 在前后端未同时升级的窗口期，旧登录页与新后端不兼容，因此该改动应作为一个完整变更交付。

## 测试

### 后端

- `UserStore`
  - 支持 `deleted_at` schema 迁移
  - tenant 级用户名唯一
  - tenant 级邮箱唯一
  - 已删除用户仍参与唯一性校验
  - 软删除不会物理删除用户记录

- `/api/admin/users`
  - 默认只返回未删除用户
  - 支持名称模糊搜索
  - 支持邮箱精确搜索
  - 支持角色筛选
  - 支持状态筛选
  - 支持禁用与启用状态切换
  - 支持批量删除部分成功响应
  - 支持重置密码并返回 `temporary_password`

- `/api/auth/login`
  - 必须带 `tenant_id`
  - 在指定 tenant 内按用户名登录成功
  - 在指定 tenant 内按邮箱登录成功
  - 相同用户名存在于不同 tenant 时，只有正确 tenant 能登录

### 前端

- `UserManagementPage`
  - 渲染搜索过滤区与操作栏
  - 搜索请求带上正确查询参数
  - 新增成功后展示临时密码结果框
  - 编辑时用户名只读
  - 状态列支持禁用与启用
  - 批量删除触发确认与正确请求
  - 重置密码触发确认并展示可复制结果

- `LoginPage`
  - 渲染租户名称输入框
  - 登录提交正确 payload
  - tenant 字段缺失时阻止提交或正确展示错误

## 风险与取舍

- 登录增加租户输入，会提高首次登录成本，但这是支持 tenant 级唯一性的必要代价。
- 已删除用户继续占用用户名和邮箱，会降低重建账号时的灵活性，但能避免“删除后复用身份”带来的审计混乱。
- 本次只做后端回收站预留而不做前端入口，会保留少量“能力已存在但 UI 未开放”的不对称状态；这是刻意选择的分阶段交付。
- 本次不改 `TenantDetailPage`，能避免与其他任务中的在途改动冲突，代价是“管理员侧 tenant 详情管理能力”继续保持现状。
