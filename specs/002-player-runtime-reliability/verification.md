# 验证记录

**日期**：2026-08-30
**平台**：Windows，交互桌面 Session 1

## 自动化

| 检查 | 结果 |
| --- | --- |
| 后端完整测试 | `420 passed` |
| Ruff | 通过 |
| Django system check | 通过 |
| Django migration check | 无未生成迁移 |
| 前端 typecheck | 通过 |
| 前端 production build | 通过；仅有既存的 >500 kB chunk 警告 |
| OpenAPI/Redocly | 通过 |
| Spec Kit validator | 通过 |
| `git diff --check` | 通过 |

## 实机预检

- PowerPoint COM ProgID 已注册：`PowerPoint.Application` CLSID 可读取。
- 项目内置 `tools/third_party/vlc/runtime/libvlc.dll` 存在。
- 当前会话只枚举到一台 `2560×1440` 显示器。
- 仓库/媒体目录没有可用于四窗口验收的 PPT/PDF 素材。

因此当前主机不能完成规范要求的“四窗口、一 COM + 其余 PDF、多屏定位、50 次真实
QWebEngine 状态切换和 10 分钟真实直播”现场验收。相关步骤保留在 `quickstart.md`，
T060 继续保持未完成，不能以自动化结果替代。
