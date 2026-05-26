from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("playback", "0019_alter_mediasource_keep_alive"),
    ]

    operations = [
        migrations.AddField(
            model_name="mediasource",
            name="ppt_backend",
            field=models.CharField(
                choices=[
                    ("libreoffice", "LibreOffice（稳定）"),
                    ("powerpoint", "Microsoft PowerPoint"),
                ],
                default="libreoffice",
                help_text="仅 PPT 源使用；打开放映时可被单次临时选择覆盖。",
                max_length=24,
                verbose_name="PPT 播放器",
            ),
        ),
        migrations.AddField(
            model_name="playbacksession",
            name="ppt_backend",
            field=models.CharField(
                choices=[
                    ("libreoffice", "LibreOffice（稳定）"),
                    ("powerpoint", "Microsoft PowerPoint"),
                ],
                default="libreoffice",
                help_text="记录当前窗口本次 PPT 放映实际使用的播放器。",
                max_length=24,
                verbose_name="当前 PPT 播放器",
            ),
        ),
        migrations.AlterField(
            model_name="playbacksession",
            name="pending_command",
            field=models.CharField(
                blank=True,
                choices=[
                    ("", "无"),
                    ("open", "打开源"),
                    ("play", "播放"),
                    ("pause", "暂停"),
                    ("stop", "停止"),
                    ("close", "关闭"),
                    ("seek", "跳转"),
                    ("next", "下一页/下一项"),
                    ("prev", "上一页/上一项"),
                    ("goto", "跳转到指定页"),
                    ("set_loop", "设置循环播放"),
                    ("set_volume", "设置音量"),
                    ("set_mute", "设置静音"),
                    ("ppt_media", "控制 PPT 当前页媒体"),
                    ("reset_ppt", "重置 PPT 放映"),
                    ("show_id", "显示窗口 ID"),
                ],
                default="",
                max_length=32,
                verbose_name="待执行指令",
            ),
        ),
    ]
