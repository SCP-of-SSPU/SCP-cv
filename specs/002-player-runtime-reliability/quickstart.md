# Quickstart: 播放器 Runtime 可靠性与热切换

## 自动化验证

```powershell
uv run pytest tests/test_playback_command_queue.py tests/test_background_audio_command_queue.py tests/test_background_audio_service.py tests/test_background_audio_handlers.py tests/test_player_controller.py tests/test_player_controller_command_ack.py tests/test_player_controller_open_recovery.py tests/test_player_controller_ppt_async_open.py tests/test_ppt_adapter.py tests/test_ppt_com_worker.py tests/test_powerpoint_slot.py tests/test_preheat_pool.py tests/test_web_adapter.py tests/test_srt_stream_adapter.py tests/test_run_player_command.py tests/test_headless_launcher.py -q
uv run pytest -q
uv run ruff check scp_cv tests
```

前端与合同：

```powershell
Set-Location frontend
npm run typecheck
npm run build
Set-Location ..
redocly lint docs/openapi.yaml
```

## Windows 实机验证

1. 登录真实 Windows 10/11 交互桌面，连接至少两台显示器，启动 `runall` 或四个 headless 播放器。确认每个窗口只绑定一个显示器，设置页无左右拼接选项。
2. 准备四个演示文稿并在不同窗口同时打开。任务管理器和播放器日志必须显示最多一个由本系统持有的 PowerPoint COM 放映；其余窗口明确显示 PDF 模式并可独立翻页。关闭 COM 窗口后，PDF 窗口不得自动升级。
3. 准备两个需要登录/滚动状态的网页源。等待预热完成，在两个源间切换 50 次；用页面标题、滚动位置和登录态确认同一个页面实例被复用，日志不得出现重复导航。
4. 启用直播 `keep_alive`，运行至少 10 分钟后切入；日志应显示续热或有效认领而非固定 TTL 冷启动。
5. 在命令已领取但尚未执行、父进程收到 Ctrl+C、子进程异常退出、COM/VLC 清理步骤失败等场景分别注入故障。确认命令可恢复、子进程先协作退出、资源逐步清理，并且日志包含窗口/源/阶段。

## 回滚

停止播放器和 Web 服务，恢复上一版本代码与数据库 migration；若现场存在本系统启动的残留 PowerPoint，使用播放器日志中的 PID 清理，不要关闭用户自行启动的 PowerPoint。恢复后删除新队列表中的 processing 租约只能通过服务命令或等待租约过期完成。
