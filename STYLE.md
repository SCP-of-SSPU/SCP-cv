# STYLE

本文记录 SCP-cv 的代码、界面和文档风格约定。更具体的目录规则以对应代码附近的既有模式为准。

## 1. 通用原则

- 命名表达业务语义，不使用 `tmp`、`foo`、`bar`、`data`、`obj` 等弱命名。
- 变更保持最小影响面，优先复用现有服务、组件、store 和工具函数。
- 单文件超过 500 行时优先拆分。
- 注释解释意图、约束、边界和风险，不重复代码字面含义。
- 不保留假成功、空实现和未接线的伪功能。

## 2. Python

- 使用类型注解，函数返回值显式标注。
- 业务逻辑优先放在 `scp_cv/services/` 或对应 app 的服务层，不把复杂逻辑堆在 view 中。
- Django 管理命令需要可测试，外部进程启动逻辑要便于 monkeypatch。
- Windows 现场相关路径使用 `pathlib.Path`，避免手写路径拼接。
- 错误信息面向现场排查，说明缺少什么、在哪里修复、下一步做什么。

## 3. TypeScript / Vue

- API 类型集中在服务或 store 附近维护，避免组件内散落重复接口。
- 控制台状态由 Pinia store 承载，组件只处理展示和局部交互。
- 异步请求必须覆盖 loading、error、empty 或禁用态。
- 图标优先使用既有设计系统图标注册，不手写一次性 SVG。
- 组件 props 和 emits 保持显式类型。

## 4. CSS

- 使用 `frontend/src/styles/tokens.css` 中的设计令牌。
- 不在业务组件中散落十六进制颜色、阴影和任意圆角。
- 固定格式控件需要稳定尺寸，避免 hover、加载态或长文本导致布局跳动。
- 移动端触控目标不小于 44px。
- 焦点态必须可见，不移除 `outline` 后不提供替代。

## 5. 前端视觉规范

- 控制台是现场运维工具，优先清晰、密集、稳定，不做营销式 hero。
- 关键状态必须文本和颜色同时表达。
- 危险动作使用确认或明确的危险语义。
- 页面主操作和次操作层级明确，不同时出现多个同权重主按钮。
- 手机端保持底部导航和主要操作可达。

## 6. 文档

- 面向现场使用者的内容写入 `docs/使用文档.md`。
- 面向维护者的内容写入 `docs/维护文档.md`。
- API 合同只保留 `docs/openapi.yaml`。
- 变更记录写入 `docs/CHANGELOG.md`，使用中文、结果导向、可追溯描述。
- 删除或迁移脚本、配置、文档时，同步清理所有引用。

## 7. 验证

常用验证命令：

```powershell
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
uv run pytest tests/ -v
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

针对性修复可先运行相关测试，但交付前应说明完整验证是否完成。
