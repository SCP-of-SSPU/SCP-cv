# VLC / libVLC

播放器使用 VLC (libVLC) 实现 SRT 流低延迟播放。

运行前需满足以下任一条件：

- 系统已安装 Windows x64 VLC，默认位于 `C:\Program Files\VideoLAN\VLC`
- 已将 Windows x64 VLC zip 包解压到项目内置运行时目录：

```text
tools/third_party/vlc/runtime/
```

关键运行时文件：

- `runtime/libvlc.dll` — python-vlc 嵌入式播放所需的动态链接库
- `runtime/libvlccore.dll` — libVLC 核心库
- `runtime/plugins/` — VLC 解复用、解码、访问协议与输出插件目录

该目录中的 runtime 文件体积较大，不纳入版本控制；如系统已安装 VLC，播放器也会自动尝试使用 `Program Files/VideoLAN/VLC`。
