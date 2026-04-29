# SCP-cv 实施 TODO

## 完成状态

- 本计划已完成并验证通过。
- 后端、前端、文档已按独立可审查块提交并推送。
- 设备开关机按已确认约束作为占位状态接口实现，响应中明确 `is_placeholder=true`，不声明已接入物理硬件协议。
- 系统音量入口已稳定接入运行态，响应中明确 `system_synced=false` 和 `backend=runtime_state`，避免误判为已调用 Windows Core Audio。
- 完整验证命令已通过：`uv run pytest tests/ -q`、`uv run ruff check .`、`uv run python manage.py check`、`npm --prefix frontend run typecheck`、`npm --prefix frontend run build`。

## 已确认约束

- 大屏显示状态只使用 `single` / `double`，`full` 视为笔误并统一改为 `single`。
- 开关机卡片包含三个设备：`拼接屏` 提供 `开机` / `关机` 两个按钮，`电视左` 与 `电视右` 各提供一个切换按钮。
- 允许按独立可审查块提交并推送到远端。
- 第三方可执行文件需要移出 `.gitignore` 并纳入 Git。

## 基础修复

- 修复播放器窗口打开后可能跨屏全屏过大：避免 `setGeometry()` 后被 `showFullScreen()` 覆盖目标屏几何。
- 修复 `Unexpected token '<'`：前端请求层检查 `Content-Type`，对 HTML/空响应返回稳定错误信息。
- 修复网页连接不上/无法控制：增强 API base、Vite proxy、SSE 重连和后端局域网访问说明。
- 修复 MediaMTX 局域网连接：统一 SRT 端口与 host 生成，更新配置与文档。
- 将第三方 `.exe` / `.dll` 依赖从 ignore 规则中移出并提交。

## 后端重构

- 扩展媒体源模型，支持文件夹、原始文件名、文件大小、MIME、临时源、过期时间和元数据。
- 实现源管理 API：文件夹 CRUD、上传、下载、移动、临时上传、临时源清理。
- 重构预案模型，支持四个窗口内容、音量状态、大屏 `single` / `double`、三态语义（未设置/空/设置）和置顶排序。
- 实现预案 API：新增、编辑、删除、置顶、激活、导入当前状态。
- 增加系统音量服务和 API，先保证 Windows 系统音量同步入口稳定。
- 增加设备开关机占位服务和 API，返回稳定的未实现状态，不做假成功。
- 增加大屏 `single` / `double` 状态服务和脚本占位，切换时保留 TODO 说明。
- 实现窗口音频策略：窗口 3/4 始终静音，`single` 时窗口 2 静音，`double` 时窗口 1/2 不静音。
- 实现直播源离线超过 1 小时自动从源列表删除。
- 增加 PPT 资源解析模型和 API，保存幻灯片 PNG、下一页预览、提词器文本等占位能力。

## 前端重写

- 重写首页：状态显示、预案调用、文件上传、设备开关机、系统音量、大屏状态切换。
- 重写源管理：文件夹管理、上传、下载、移动、直播、视频、图片、PPT、网址源。
- 重写预案管理：新增、编辑、删除、置顶、导入当前源。
- 实现大屏左显示控制页；`single` 时页面名称为大屏显示控制。
- 实现大屏右显示控制页；`single` 时隐藏该切换卡片。
- 实现 TV 左显示控制页。
- 实现 TV 右显示控制页。
- 实现关于页：使用说明、教程和项目信息。
- 实现显示控制页通用交互：当前状态、切换源、上传临时源、上传源并保存、关闭显示。
- 按源类型展示控制卡片：直播状态、图片/网址预览、视频进度/循环/音量/播放暂停、PPT 翻页/媒体播放/PPT 状态/专注模式。
- 实现 PPT 专注页：无导航栏、返回按钮、大按钮翻页、媒体播放、提词器、当前页/下一页预览、页码状态。
- 完善桌面端、手机竖屏、平板横屏响应式布局。

## 文档与验证

- 更新 `docs/API.md`。
- 更新 `docs/使用文档.md`。
- 更新 `docs/CHANGELOG.md`。
- 更新 `README.md`。
- 补充/更新后端测试。
- 运行 `uv run pytest tests/ -v`。
- 运行 `npm --prefix frontend run typecheck`。
- 运行 `npm --prefix frontend run build`。
- 按独立块提交并推送。
