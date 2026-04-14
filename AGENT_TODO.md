# AGENT TODO

## 说明

- 本文件用于对AGENT工作时候进行工作计划，本文内除任务内容外的AGENT代表正在进行任务工作的ai智能体，用户为需求提出人/项目所有者，在任务描述或对话中的用户或AGENT可能不是该含义，若需要在任务描述或对话中准确描述工作的执行者双方，请使用斜体`*AGENT*`和`*用户*`。
- AGENT需要遵循如下规则：

1. **无论什么原因都不要认定所有任务均已完成。**
2. 需要逐个任务进行完成，**不可跳过、忽略**；对于执行中的任务，请在执行的任务行前添加`>`字符创建块引用(需要在`-`之后，效果为`- > 执行中的任务`)。
3. 对于已经完成的任务，请进行任务转移，需要转移本文件中对该项任务的描述和标题，请直接剪切到已完成任务中，对于说明了不要修改本行的任务请不要进行操作。
4. 对于每个任务，除极其简单的任务外，都需要规划待办事项，且待办事项的最后一条都应当为回到AGENT_TODO.md进行下一个任务，而不是将所有任务均放到待办中！。
5. 注意该文件可能在执行过程中由人工进行变动，请务必在每一轮任务完成后进行查看，而不是直接将所有任务放入记忆中，同时也不要手动恢复某些被删除的内容 ，因为这可能是用户介入删除的。
6. 需要与用户互动时，请使用Interactive MCP，不要使用askQuestion工具(由于Autopilot模式下askQuestion无法得到真实的用户答复)。
7. 鼓励使用MCP、skills、外部cli等工具，若有新工具需求也可告知用户进行安装配置。
8. 鼓励在执行过程中的不确定项上与用户进行互动。
9. 鼓励并行使用subagent以提升效率和节省上下文，但要确保不会导致任务过度阻塞。
10. 编辑/创建文件使用Filesystem MCP

## 任务

- 探索本仓库(若本次是新会话)(**不要修改此行，若非新会话，忽略本任务**)
- > 为pyside6初始启动添加GUI页面，用于选择单屏幕/双屏幕拼接功能，--dev模式使用带标题的窗口，无--dev则使用无边框窗口/全屏，在这个GUI中，选择屏幕阶段则在各个屏幕上显示按钮，双屏幕模式需要选择左/右
- 根据如下内容进行PPT控制设计，注意还需要设计文件保存和打开的逻辑，并重新完善django的前端页面
```markdown
可以，把它改成一套**“gRPC 控制面 + PySide 播放面 + 媒体源适配层”**的结构就行。

你现在这套方案里，最合适的做法是：

* **网页/Django**：上传文件、选择源、下发控制命令
* **本机播放器进程**：PySide 窗口真正显示内容
* **gRPC**：只负责“控制播放器”和“订阅播放器状态”
* **媒体源适配层**：把 PPT、视频、网页流、自定义流统一成同一套 `open / play / pause / stop / seek / close` 接口

这样以后你不只是能播 PPT，还能播本地 MP4、HTTP 视频、RTSP、中转流，甚至你自己定义的数据流。gRPC 的服务定义天然适合这种“命令 + 状态”的模型；在 Python gRPC 里，低频控制命令更适合用 unary RPC，持续状态通知再用 server-streaming，官方也提到 Python 的 streaming RPC 会额外引入线程开销，比 unary 更重。([gRPC][1])

---

## 先定一条原则

**不要把 gRPC 设计成 `NextPpt / PrevPpt / PauseVideo / ResumeVideo` 这种业务接口。**
而是统一成：

* `OpenSource`
* `Play`
* `Pause`
* `Stop`
* `Seek`
* `Close`
* `GetState`
* `WatchState`

也就是：**上层只管“当前槽位里是什么源、它现在是什么状态”**，不关心底下是 PPT 还是视频。
真正的差异由适配器处理。

---

## 推荐的结构

```text
浏览器
  ↓ HTTP / WebSocket
Django
  ├─ 保存上传文件
  ├─ 展示源列表
  └─ 调本机 gRPC Player
          ↓
Local Player Daemon (Windows 当前桌面会话)
  ├─ PySide 窗口
  ├─ PlayerManager
  ├─ PptSourceAdapter
  ├─ VideoSourceAdapter
  ├─ CustomStreamSourceAdapter
  └─ gRPC Server
```

如果你的网页想**直接**调 gRPC，而不是经 Django 中转，浏览器侧通常要走 **gRPC-Web**，并配一个代理层；官方资料里也提到浏览器环境下主要支持 unary 和部分 server streaming，客户端流式能力受限。([gRPC][2])

---

## 1）gRPC 接口怎么定义

建议直接按“会话 + 槽位 + 源类型”来设计。

### `player.proto`

```proto
syntax = "proto3";

package player;

service PlayerService {
  rpc OpenSource(OpenSourceRequest) returns (OpenSourceReply);
  rpc Play(ControlRequest) returns (ControlReply);
  rpc Pause(ControlRequest) returns (ControlReply);
  rpc Stop(ControlRequest) returns (ControlReply);
  rpc Seek(SeekRequest) returns (ControlReply);
  rpc Close(ControlRequest) returns (ControlReply);
  rpc GetState(GetStateRequest) returns (StateReply);
  rpc WatchState(WatchStateRequest) returns (stream StateReply);
}

enum SourceType {
  SOURCE_UNKNOWN = 0;
  SOURCE_PPT = 1;
  SOURCE_VIDEO = 2;
  SOURCE_AUDIO = 3;
  SOURCE_IMAGE = 4;
  SOURCE_WEB = 5;
  SOURCE_CUSTOM_STREAM = 6;
}

enum PlaybackState {
  STATE_UNKNOWN = 0;
  STATE_IDLE = 1;
  STATE_LOADING = 2;
  STATE_READY = 3;
  STATE_PLAYING = 4;
  STATE_PAUSED = 5;
  STATE_STOPPED = 6;
  STATE_ERROR = 7;
}

message OpenSourceRequest {
  string slot_id = 1;          // 比如 main / left / right
  SourceType source_type = 2;
  string uri = 3;              // file:///... 或 http://... 或 rtsp://...
  bool autoplay = 4;
  map<string, string> options = 5;
}

message OpenSourceReply {
  bool ok = 1;
  string session_id = 2;
  string message = 3;
}

message ControlRequest {
  string session_id = 1;
}

message SeekRequest {
  string session_id = 1;
  int64 position_ms = 2;
}

message GetStateRequest {
  string session_id = 1;
}

message WatchStateRequest {
  string session_id = 1;
}

message StateReply {
  string session_id = 1;
  PlaybackState state = 2;
  int64 position_ms = 3;
  int64 duration_ms = 4;
  string current_uri = 5;
  string message = 6;
}

message ControlReply {
  bool ok = 1;
  StateReply state = 2;
}
```

这套定义的好处是：
**PPT、视频、自定义流在 gRPC 层完全同构。**

---

## 2）“自定义媒体源”的本质：适配器

你真正要做的不是“gRPC 播放媒体”，而是让 gRPC 调用一个统一接口：

```python
class SourceAdapter:
    def open(self, uri: str, options: dict): ...
    def play(self): ...
    def pause(self): ...
    def stop(self): ...
    def seek(self, position_ms: int): ...
    def close(self): ...
    def get_state(self) -> dict: ...
```

然后按源类型实现：

* `PptSourceAdapter`
* `VideoSourceAdapter`
* `WebSourceAdapter`
* `CustomStreamSourceAdapter`

---

## 3）视频/音频/自定义流怎么做播放与暂停

如果你的“自定义媒体源”本质上是**视频或音频**，PySide 里最直接的是 `QMediaPlayer`。Qt 官方文档里明确给了这些能力：

* `setSource(QUrl)`：设置本地文件或 URL 源
* `setSourceDevice(QIODevice, QUrl)`：设置你自己的流设备
* `play()`
* `pause()`
* `stop()`
* `playbackStateChanged`
* `QVideoWidget` 可作为视频输出窗口 ([Qt 文档][3])

也就是说：

### 普通文件/URL 源

用：

```python
player.setSource(QUrl.fromLocalFile(path))
# 或
player.setSource(QUrl(url))
```

### 你自己的“自定义流”

如果你不是给文件路径，而是你自己从网络/管道/缓存里持续喂数据，可以做一个 `QIODevice`，再用：

```python
player.setSourceDevice(device, QUrl("stream://custom"))
```

Qt 文档明确说明 `setSourceDevice()` 就是从设备读取媒体数据。([Qt 文档][3])

### 暂停/恢复

`QMediaPlayer::pause()` 会让播放进入暂停态，恢复时从暂停位置继续；官方文档对 `PausedState` 也是这么定义的。([Qt 文档][4])

---

## 4）最关键的一点：gRPC 线程不要直接碰 PySide 控件

gRPC Server 往往不在 Qt UI 主线程里跑。
所以你不能在 gRPC handler 里直接：

```python
player.play()
widget.setGeometry(...)
```

正确方式是：

* gRPC 收到命令
* 把命令投递给 Qt 主线程
* 主线程去操作 `QMediaPlayer / QWidget / COM`

做法可以是：

* Qt `Signal`
* `QMetaObject.invokeMethod(..., Qt.QueuedConnection, ...)`
* 或一个线程安全队列 + `QTimer` 轮询

也就是：

```python
# gRPC线程
manager.request_play(session_id)

# Qt主线程
@Slot(str)
def do_play(self, session_id):
    self.sessions[session_id].adapter.play()
```

这个拆法很重要，不然 UI 和 COM 都容易出问题。

---

## 5）一个可直接落地的视频源适配器

```python
from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget

class VideoSourceAdapter(QObject):
    state_changed = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.video_widget = QVideoWidget()
        self.audio_output = QAudioOutput()
        self.player = QMediaPlayer()

        self.player.setAudioOutput(self.audio_output)
        self.player.setVideoOutput(self.video_widget)

        self.player.playbackStateChanged.connect(self._emit_state)
        self.player.positionChanged.connect(self._emit_state)
        self.player.durationChanged.connect(self._emit_state)
        self.player.mediaStatusChanged.connect(self._emit_state)

        self.current_uri = None

    def open(self, uri: str, options: dict | None = None):
        self.current_uri = uri
        self.player.setSource(QUrl(uri))

    def play(self):
        self.player.play()

    def pause(self):
        self.player.pause()

    def stop(self):
        self.player.stop()

    def seek(self, position_ms: int):
        self.player.setPosition(position_ms)

    def close(self):
        self.player.stop()
        self.player.setSource(QUrl())

    def get_state(self):
        return {
            "uri": self.current_uri or "",
            "position_ms": self.player.position(),
            "duration_ms": self.player.duration(),
            "qt_state": int(self.player.playbackState()),
        }

    def _emit_state(self, *args):
        self.state_changed.emit(self.get_state())
```

---

## 6）自定义流源适配器怎么做

如果你想做的是：

* 外部推一个自定义媒体流到本机
* 本机窗口里播放
* 再由 gRPC 控制播放/暂停

那可以这样分两层：

### 方案 A：你的流最终能表现为 URL

例如：

* `http://127.0.0.1:9000/live.mp4`
* `rtsp://127.0.0.1/live`
* `file:///...`

那最简单，直接还是 `QMediaPlayer.setSource(QUrl(...))`。

### 方案 B：你的流是你自己维护的字节流

比如：

* 自定义 TCP 协议
* 共享内存
* 环形缓冲区
* 你自己的封包格式

那就自己做一个 `QIODevice` 子类，把解复用后的媒体字节交给 `setSourceDevice()`。
这个适合你已经有边缘服务或自定义接入协议的情况。Qt 官方文档说明它就是从 `QIODevice` 读取媒体。([Qt 文档][3])

---

## 7）PPT 在这套统一接口里怎么映射

这里要区分一下：

### 视频源的 `play/pause`

是真的媒体时间线控制。

### PPT 源的 `play/pause`

**不应该硬套成同一种语义。**

PowerPoint 官方对象模型公开得很明确的是：

* `SlideShowSettings.Run()` 启动放映
* `SlideShowWindow.View`
* `View.Next()`
* `View.Previous()` ([Microsoft Learn][5])

但它并没有像 `QMediaPlayer` 那样给你一个统一、清晰的媒体级 `play()/pause()` 接口。基于这些官方接口，可以合理推断：**PPT 更适合建模为“翻页型源”，不是“时间线媒体源”。**
所以建议：

* `PptSourceAdapter.play()`：开始放映
* `PptSourceAdapter.pause()`：做成 no-op，或“冻结自动前进/屏蔽翻页输入/覆盖暂停层”
* `PptSourceAdapter.stop()`：退出放映
* 真正的主控制仍然是 `next / previous / goto`

如果你以后一定要“PPT 也能严格暂停/恢复”，更稳的路线反而是：

* 把 PPT 导出为视频，再按视频源播放
* 或导出为图片序列，再自己控页

---

## 8）gRPC 服务端怎么写

推荐让 gRPC 只做**命令转发**和**状态查询**。

```python
import grpc
from concurrent import futures

class PlayerServiceServicer(player_pb2_grpc.PlayerServiceServicer):
    def __init__(self, manager):
        self.manager = manager   # Qt主线程里的 PlayerManager

    def OpenSource(self, request, context):
        session_id = self.manager.open_source(
            slot_id=request.slot_id,
            source_type=request.source_type,
            uri=request.uri,
            autoplay=request.autoplay,
            options=dict(request.options),
        )
        return player_pb2.OpenSourceReply(
            ok=True,
            session_id=session_id,
            message="opened",
        )

    def Play(self, request, context):
        state = self.manager.play(request.session_id)
        return player_pb2.ControlReply(ok=True, state=state)

    def Pause(self, request, context):
        state = self.manager.pause(request.session_id)
        return player_pb2.ControlReply(ok=True, state=state)

    def Stop(self, request, context):
        state = self.manager.stop(request.session_id)
        return player_pb2.ControlReply(ok=True, state=state)

    def Seek(self, request, context):
        state = self.manager.seek(request.session_id, request.position_ms)
        return player_pb2.ControlReply(ok=True, state=state)
```

你会发现，真正难的不是 gRPC，而是 `PlayerManager`：

* 维护当前 `session_id -> adapter`
* 把 gRPC 线程命令切到 Qt 主线程
* 汇总状态
* 把状态广播给 `WatchState`

---

## 9）状态订阅怎么做

你网页上一般会需要看到：

* 当前播放中/已暂停
* 进度
* 当前文件
* 错误信息

这里建议：

* `Play/Pause/Seek/Stop`：都用 unary RPC
* `WatchState`：server-streaming，用于推送状态变化

这么做和 gRPC 官方的 RPC 模型是匹配的；但在 Python 里，streaming 比 unary 更重，所以只把它用在“少量状态订阅”上，不要把所有控制都做成长连接。([gRPC][1])

---

## 10）网页这一层怎么接

你有两种接法：

### 接法 1：网页 → Django → gRPC → 本机播放器

这是最适合你当前架构的。
浏览器继续调 Django 的 HTTP/WebSocket；Django 当 control gateway，再去调本机 gRPC。

优点：

* 简单
* 权限、日志、文件路径映射都在 Django 里
* 浏览器不用处理 gRPC-Web

### 接法 2：网页 → gRPC-Web → Envoy → gRPC Player

可以做，但会更复杂。浏览器环境下 gRPC-Web 的能力和原生 gRPC 不完全一样，一般适合 unary 和部分 server streaming。([gRPC][2])

你现在这类本机控制系统，我更建议第一种。

---

## 11）给你一个最实用的落地建议

把“自定义媒体源播放与暂停”分成两类看：

### A. 真正的媒体源

例如 MP4、HTTP 视频、RTSP、自定义解复用流
→ 用 `VideoSourceAdapter`
→ `play/pause/seek/stop` 都是真语义

### B. 幻灯片源

例如 PPT/PPTX
→ 用 `PptSourceAdapter`
→ 主语义是 `start/next/prev/goto/close`
→ `pause` 只是兼容接口，不要强行当成和视频完全一样

---

## 12）最终推荐方案

你这套系统里，我建议直接定成：

* **gRPC 合同不区分业务类型**
* **底层用 adapter 区分源类型**
* **视频/音频/自定义流走 `QMediaPlayer`**
* **PPT 继续走 PowerPoint COM**
* **Qt 主线程负责所有 UI/播放器操作**
* **Django 仍然做网页、存储、权限和调度**

一句话就是：

**“gRPC 控制统一接口，PySide 负责呈现，适配器负责具体播放语义。”**

这样后面你加“本地视频、网页播放器、OBS 中转、自定义协议流”，都不用改 Web 端 API，只是多写一个 adapter。

如果你愿意，我下一条直接给你一份**完整的 proto + Python gRPC Server + PySide PlayerManager + VideoSourceAdapter/PptSourceAdapter 骨架代码**。

[1]: https://grpc.io/docs/what-is-grpc/core-concepts/?utm_source=chatgpt.com "Core concepts, architecture and lifecycle"
[2]: https://grpc.io/blog/state-of-grpc-web/?utm_source=chatgpt.com "The state of gRPC in the browser"
[3]: https://doc.qt.io/qt-6/ja/qmediaplayer.html?utm_source=chatgpt.com "QMediaPlayer Class | Qt Multimedia | Qt 6.11.0"
[4]: https://doc.qt.io/qt-6/qmediaplayer.html?utm_source=chatgpt.com "QMediaPlayer Class | Qt Multimedia | Qt 6.11.0"
[5]: https://learn.microsoft.com/en-us/office/vba/api/powerpoint.slideshowview?utm_source=chatgpt.com "SlideShowView object (PowerPoint)"
```

- 使用Interactive MCP对*用户*发出提问询问下一步需求(**不要结束会话，不要修改本任务，不要使用askQuestion**，此处可能需要多轮互动或持续等待，直到*用户*明确提出需求为止)

## 已完成任务

- 将mediamtx的协议修改为WebRTC，同时在mediamtx和pyside中加入同步帧功能，需要做到亚秒级的延迟，且不会因为时间变长延迟变高
- 根据需求I进行工作
- 在docs中新建使用文档
- 在tools文件夹中创建一个testdata文件夹，并在这个文件夹内创建一些测试用的PPT
