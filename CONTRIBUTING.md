# CONTRIBUTING

感谢参与 SCP-cv 维护。这个项目直接服务上海第二工业大学 28#108 多媒体显示系统，贡献时优先保证现场稳定、变更可验证、回滚成本低。

## 1. 开始前

```powershell
git status --short --branch
git pull --rebase
uv sync
npm ci --prefix frontend
```

如果工作区存在未提交内容，先判断是否与当前任务相关。不要覆盖或回滚他人的改动。

## 2. 分支与提交

提交信息格式：

```text
type(scope): 中文摘要
```

可用类型：

- `feat`
- `fix`
- `refactor`
- `docs`
- `style`
- `test`
- `perf`
- `build`
- `ci`
- `chore`
- `revert`

示例：

```text
fix(frontend): 修复前端环境变量优先级
docs(repo): 补充维护文档
```

每个独立可审查块单独提交。不要把格式化、依赖升级、业务修复和文档大改混成一个不可审查提交。

## 3. 代码要求

- Python 代码遵循 PEP 8、类型注解和项目既有服务分层。
- Vue / TypeScript 代码遵循 `frontend/src/` 既有组件、store、composable 和样式结构。
- 单文件超过 500 行时应优先拆分，不继续堆积实现。
- 不保留空实现、假成功逻辑或无说明占位。
- 如确需保留未完成项，只能使用 `TODO:` 或 `FIXME:`，并写清原因、影响、后续动作和风险。
- 手写注释解释意图、约束和边界，不用注释弥补弱命名。

## 4. 文档要求

以下变更必须同步文档：

- API 合同
- 配置项
- 运行或部署流程
- 权限、设备、端口和平台支持
- 错误处理和联调方式
- 第三方运行时资产

文档入口：

- `README.md`
- `docs/使用文档.md`
- `docs/维护文档.md`
- `docs/openapi.yaml`
- `docs/CHANGELOG.md`
- `STYLE.md`

## 5. 验证要求

后端：

```powershell
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
uv run pytest tests/ -v
```

前端：

```powershell
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

启动流程或环境变量变更：

```powershell
uv run pytest tests/test_runall_command.py -v
```

无法运行某项验证时，在提交或交付说明中写明原因和剩余风险。

## 6. 不提交的内容

不要提交：

- `.env`
- `frontend/.env`
- `.claude/`
- `.oms/`
- `.playwright-cli/`
- `.playwright-mcp` / `.playwright-mcp/`
- `.pytest_cache/`
- `.ruff_cache/`
- `node_modules/`
- 上传媒体、日志、临时测试脚本
- `requirements*.txt`

依赖以 `uv.lock`、`package-lock.json` 和 `frontend/package-lock.json` 为准。

## 7. Pull Request 检查清单

- 变更范围清晰，没有夹带无关重构。
- 相关测试已运行并通过。
- 影响用户或现场运维的行为已更新文档。
- 没有提交本地缓存、日志、上传文件或密钥。
- `docs/CHANGELOG.md` 已记录用户可感知变更。
