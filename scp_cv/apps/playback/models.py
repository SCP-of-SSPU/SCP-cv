#!/user/bin/env python
# -*- coding: UTF-8 -*-
'''
播放系统数据模型：统一媒体源（MediaSource）与播放会话（PlaybackSession）。
MediaSource 统一管理所有可播放源（PPT、视频、RTSP 流等），
PlaybackSession 维护当前播放状态与指令分发。
@Project : SCP-cv
@File : models.py
@Author : Qintsg
@Date : 2026-04-29
'''
from __future__ import annotations

from django.db import models


# ════════════════════════════════════════════════════════════════
# 枚举常量
# ════════════════════════════════════════════════════════════════


class SourceType(models.TextChoices):
    """统一媒体源类型枚举，覆盖所有可播放内容。"""

    PPT = "ppt", "PPT 演示文稿"
    VIDEO = "video", "视频"
    AUDIO = "audio", "音频"
    IMAGE = "image", "图片"
    WEB = "web", "网页"
    CUSTOM_STREAM = "custom_stream", "自定义流"
    RTSP_STREAM = "rtsp_stream", "RTSP 流"
    SRT_STREAM = "srt_stream", "SRT 流"


class PlaybackMode(models.TextChoices):
    """播放目标布局。"""

    SINGLE = "single", "单屏"
    LEFT_RIGHT_SPLICE = "left_right_splice", "左右拼接"


class BigScreenMode(models.TextChoices):
    """大屏显示状态：single 仅窗口 1，double 窗口 1+2 左右各半。"""

    SINGLE = "single", "单屏"
    DOUBLE = "double", "双屏"


class PlaybackState(models.TextChoices):
    """播放会话状态。"""

    IDLE = "idle", "待机"
    LOADING = "loading", "加载中"
    PLAYING = "playing", "播放中"
    PAUSED = "paused", "暂停"
    STOPPED = "stopped", "已停止"
    ERROR = "error", "异常"


class PlaybackCommand(models.TextChoices):
    """播放控制指令枚举，由 Django 写入、播放器轮询消费。"""

    NONE = "", "无"
    OPEN = "open", "打开源"
    PLAY = "play", "播放"
    PAUSE = "pause", "暂停"
    STOP = "stop", "停止"
    CLOSE = "close", "关闭"
    SEEK = "seek", "跳转"
    NEXT = "next", "下一页/下一项"
    PREV = "prev", "上一页/上一项"
    GOTO = "goto", "跳转到指定页"
    SET_LOOP = "set_loop", "设置循环播放"
    SET_VOLUME = "set_volume", "设置音量"
    SET_MUTE = "set_mute", "设置静音"
    SHOW_ID = "show_id", "显示窗口 ID"


class SourceState(models.TextChoices):
    """预案中窗口内容的三态语义。"""

    UNSET = "unset", "未设置（保持原有）"
    EMPTY = "empty", "清空（黑屏）"
    SET = "set", "已设置（使用绑定源）"


class DeviceType(models.TextChoices):
    """设备类型枚举，用于开关机卡片占位。"""

    SPLICE_SCREEN = "splice_screen", "拼接屏"
    TV_LEFT = "tv_left", "电视左"
    TV_RIGHT = "tv_right", "电视右"


# ════════════════════════════════════════════════════════════════
# 媒体源模型
# ════════════════════════════════════════════════════════════════


class MediaFolder(models.Model):
    """
    媒体源文件夹，支持层级组织。
    """

    name = models.CharField(
        max_length=255,
        verbose_name="文件夹名称",
    )
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="children",
        verbose_name="父文件夹",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="创建时间",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="更新时间",
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "媒体文件夹"
        verbose_name_plural = "媒体文件夹"

    def __str__(self) -> str:
        return self.name


class MediaSource(models.Model):
    """
    统一媒体源模型，所有可播放内容的注册表。
    文件型源（PPT/视频/图片等）通过上传或本地路径录入；
    RTSP 流型源由 MediaMTX 自动发现后同步创建。
    """

    source_type = models.CharField(
        max_length=24,
        choices=SourceType.choices,
        db_index=True,
        verbose_name="源类型",
    )
    name = models.CharField(
        max_length=255,
        verbose_name="显示名称",
    )
    uri = models.CharField(
        max_length=1024,
        verbose_name="资源地址",
        help_text="文件绝对路径、URL 或流标识符",
    )
    uploaded_file = models.FileField(
        upload_to="uploads/%Y%m%d/",
        blank=True,
        verbose_name="上传文件",
        help_text="通过 Web 上传的文件存储路径",
    )
    # 仅 RTSP_STREAM 类型使用，关联自动发现的流记录
    stream_identifier = models.CharField(
        max_length=255,
        blank=True,
        db_index=True,
        verbose_name="流标识符",
        help_text="RTSP 流的 MediaMTX 路径标识",
    )
    is_available = models.BooleanField(
        default=True,
        verbose_name="是否可用",
        help_text="文件是否存在 / 流是否在线",
    )

    # ── 文件夹与文件元数据 ──
    folder = models.ForeignKey(
        MediaFolder,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sources",
        verbose_name="所属文件夹",
    )
    original_filename = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="原始文件名",
        help_text="上传时的原始文件名，用于下载",
    )
    file_size = models.BigIntegerField(
        default=0,
        verbose_name="文件大小（字节）",
    )
    mime_type = models.CharField(
        max_length=127,
        blank=True,
        verbose_name="MIME 类型",
    )

    # ── 临时源 ──
    is_temporary = models.BooleanField(
        default=False,
        verbose_name="是否临时源",
        help_text="临时源在切换离开后自动删除",
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="过期时间",
        help_text="临时源过期后自动清理",
    )

    # ── 扩展元数据 ──
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="扩展元数据",
        help_text="存储 PPT 解析资源 ID 等扩展信息",
    )

    # ── 时间戳 ──
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="创建时间",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "媒体源"
        verbose_name_plural = "媒体源"

    def __str__(self) -> str:
        return f"[{self.get_source_type_display()}] {self.name}"


class PptResource(models.Model):
    """
    PPT 解析资源，存储幻灯片 PNG 预览和提词器文本。
    与 MediaSource 关联，删除 PPT 时一并删除。
    """

    source = models.ForeignKey(
        MediaSource,
        on_delete=models.CASCADE,
        related_name="ppt_resources",
        verbose_name="关联 PPT 源",
    )
    page_index = models.PositiveIntegerField(
        verbose_name="页码（从 1 开始）",
    )
    slide_image = models.CharField(
        max_length=512,
        blank=True,
        verbose_name="幻灯片 PNG 路径",
    )
    next_slide_image = models.CharField(
        max_length=512,
        blank=True,
        verbose_name="下一页 PNG 路径",
    )
    speaker_notes = models.TextField(
        blank=True,
        default="",
        verbose_name="演讲者备注/提词器文本",
    )
    has_media = models.BooleanField(
        default=False,
        verbose_name="是否包含媒体",
        help_text="该页是否包含视频/音频媒体对象",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="创建时间",
    )

    class Meta:
        ordering = ["source", "page_index"]
        unique_together = [("source", "page_index")]
        verbose_name = "PPT 资源"
        verbose_name_plural = "PPT 资源"

    def __str__(self) -> str:
        return f"{self.source.name} - 第{self.page_index}页"


# ════════════════════════════════════════════════════════════════
# 播放会话模型
# ════════════════════════════════════════════════════════════════


class PlaybackSession(models.Model):
    """
    播放会话模型，每个输出窗口维护一个独立实例。
    通过 window_id（1-4）区分不同窗口的播放状态与指令。
    播放器进程通过轮询本表驱动播放行为。
    """

    # ── 窗口标识（1-4） ──
    window_id = models.PositiveSmallIntegerField(
        unique=True,
        verbose_name="窗口编号",
        help_text="输出窗口编号，1-4 对应四个输出显示器",
    )

    # ── 当前播放源 ──
    media_source = models.ForeignKey(
        MediaSource,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="playback_sessions",
        verbose_name="当前媒体源",
    )

    # ── 播放状态 ──
    playback_state = models.CharField(
        max_length=16,
        choices=PlaybackState.choices,
        default=PlaybackState.IDLE,
        verbose_name="播放状态",
    )

    # ── 显示配置（由启动器 GUI 写入） ──
    display_mode = models.CharField(
        max_length=24,
        choices=PlaybackMode.choices,
        default=PlaybackMode.SINGLE,
        verbose_name="显示模式",
    )
    target_display_label = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="目标显示器",
    )
    spliced_display_label = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="拼接显示器组",
    )
    is_spliced = models.BooleanField(
        default=False,
        verbose_name="是否拼接",
    )
    # ── PPT / 翻页型源状态 ──
    current_slide = models.IntegerField(
        default=0,
        verbose_name="当前页码",
    )
    total_slides = models.IntegerField(
        default=0,
        verbose_name="总页数",
    )

    # ── 时间线型源状态（视频/音频） ──
    position_ms = models.BigIntegerField(
        default=0,
        verbose_name="当前位置(ms)",
    )
    duration_ms = models.BigIntegerField(
        default=0,
        verbose_name="总时长(ms)",
    )

    # ── 音频与循环 ──
    volume = models.IntegerField(
        default=100,
        verbose_name="音量（0-100）",
    )
    is_muted = models.BooleanField(
        default=False,
        verbose_name="是否静音",
    )
    loop_enabled = models.BooleanField(
        default=False,
        verbose_name="循环播放",
        help_text="视频/音频播放完毕后是否自动重头播放",
    )

    # ── 控制指令分发（Django 写入 → 播放器消费） ──
    pending_command = models.CharField(
        max_length=32,
        choices=PlaybackCommand.choices,
        default=PlaybackCommand.NONE,
        blank=True,
        verbose_name="待执行指令",
    )
    command_args = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="指令参数",
    )

    # ── 时间戳 ──
    last_updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="最后更新",
    )

    class Meta:
        ordering = ["window_id"]
        verbose_name = "播放会话"
        verbose_name_plural = "播放会话"

    def __str__(self) -> str:
        source_label = self.media_source.name if self.media_source else "无"
        return f"窗口{self.window_id} / {source_label} / {self.get_playback_state_display()}"


# ════════════════════════════════════════════════════════════════
# 预案模型
# ════════════════════════════════════════════════════════════════


class Scenario(models.Model):
    """
    预案模型：预定义大屏/TV 的播放配置快照。
    激活时按三态语义应用各窗口内容，支持置顶排序。
    """

    # ── 基本信息 ──
    name = models.CharField(
        max_length=100,
        verbose_name="预案名称",
    )
    description = models.TextField(
        blank=True,
        default="",
        verbose_name="描述",
    )

    # ── 排序（置顶优先） ──
    sort_order = models.IntegerField(
        default=0,
        verbose_name="排序权重",
        help_text="数值越大越靠前，支持置顶",
    )

    # ── 大屏模式 ──
    big_screen_mode_state = models.CharField(
        max_length=8,
        choices=SourceState.choices,
        default=SourceState.UNSET,
        verbose_name="大屏模式状态",
    )
    big_screen_mode = models.CharField(
        max_length=8,
        choices=BigScreenMode.choices,
        default=BigScreenMode.SINGLE,
        blank=True,
        verbose_name="大屏模式",
        help_text="仅当 big_screen_mode_state=set 时生效",
    )

    # ── 音量 ──
    volume_state = models.CharField(
        max_length=8,
        choices=SourceState.choices,
        default=SourceState.UNSET,
        verbose_name="音量状态",
    )
    volume_level = models.IntegerField(
        default=100,
        verbose_name="音量等级（0-100）",
        help_text="仅当 volume_state=set 时生效",
    )

    # ── 时间戳 ──
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="创建时间",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="更新时间",
    )

    class Meta:
        ordering = ["-sort_order", "-updated_at"]
        verbose_name = "预案"
        verbose_name_plural = "预案"

    def __str__(self) -> str:
        return self.name


class ScenarioTarget(models.Model):
    """
    预案中的单个窗口目标配置。
    通过 source_state 三态语义决定激活时行为：
    - unset：激活时不改变该窗口
    - empty：激活时关闭该窗口（黑屏）
    - set：激活时打开绑定的媒体源
    """

    scenario = models.ForeignKey(
        Scenario,
        on_delete=models.CASCADE,
        related_name="targets",
        verbose_name="所属预案",
    )
    window_id = models.PositiveSmallIntegerField(
        verbose_name="窗口编号",
        help_text="1-4 对应四个输出窗口",
    )
    source_state = models.CharField(
        max_length=8,
        choices=SourceState.choices,
        default=SourceState.UNSET,
        verbose_name="内容状态",
    )
    source = models.ForeignKey(
        MediaSource,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="scenario_targets",
        verbose_name="绑定媒体源",
        help_text="仅当 source_state=set 时生效",
    )
    autoplay = models.BooleanField(
        default=True,
        verbose_name="自动播放",
        help_text="仅当 source_state=set 时生效",
    )
    resume = models.BooleanField(
        default=True,
        verbose_name="保留进度",
        help_text="相同源已打开时保留当前进度，否则从头播放",
    )

    class Meta:
        ordering = ["window_id"]
        unique_together = [("scenario", "window_id")]
        verbose_name = "预案窗口目标"
        verbose_name_plural = "预案窗口目标"

    def __str__(self) -> str:
        state_label = self.get_source_state_display()
        if self.source_state == SourceState.SET and self.source:
            return f"窗口{self.window_id}: {self.source.name}"
        return f"窗口{self.window_id}: {state_label}"


# ════════════════════════════════════════════════════════════════
# 设备开关机占位模型
# ════════════════════════════════════════════════════════════════


class DeviceEndpoint(models.Model):
    """
    设备端点占位模型，记录可控制的物理设备。
    当前仅用于前端 UI 占位，实际控制逻辑待后续实现。
    """

    name = models.CharField(
        max_length=100,
        verbose_name="设备名称",
    )
    device_type = models.CharField(
        max_length=24,
        choices=DeviceType.choices,
        unique=True,
        verbose_name="设备类型",
    )
    is_powered_on = models.BooleanField(
        default=False,
        verbose_name="是否开机",
    )
    address = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="设备地址",
        help_text="IP 或串口地址，待后续实现",
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="扩展信息",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="创建时间",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="更新时间",
    )

    class Meta:
        ordering = ["device_type"]
        verbose_name = "设备端点"
        verbose_name_plural = "设备端点"

    def __str__(self) -> str:
        power_label = "开机" if self.is_powered_on else "关机"
        return f"{self.name}（{power_label}）"


# ════════════════════════════════════════════════════════════════
# 全局运行状态（单例）
# ════════════════════════════════════════════════════════════════


class RuntimeState(models.Model):
    """
    全局运行状态单例，记录当前大屏模式等全局状态。
    通过 id=1 强制单例约束。
    """

    id = models.AutoField(primary_key=True)
    big_screen_mode = models.CharField(
        max_length=8,
        choices=BigScreenMode.choices,
        default=BigScreenMode.SINGLE,
        verbose_name="当前大屏模式",
    )
    volume_level = models.IntegerField(
        default=100,
        verbose_name="系统音量（0-100）",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="最后更新",
    )

    class Meta:
        verbose_name = "运行状态"
        verbose_name_plural = "运行状态"

    def __str__(self) -> str:
        return f"大屏: {self.get_big_screen_mode_display()}, 音量: {self.volume_level}"

    @classmethod
    def get_instance(cls) -> "RuntimeState":
        """获取或创建全局单例。"""
        instance, _ = cls.objects.get_or_create(pk=1)
        return instance
