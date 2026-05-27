from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("playback", "0020_ppt_backend_selection"),
    ]

    operations = [
        migrations.AlterField(
            model_name="mediasource",
            name="ppt_backend",
            field=models.CharField(
                choices=[
                    ("libreoffice", "LibreOffice（稳定）"),
                    ("powerpoint", "Microsoft PowerPoint"),
                    ("wps", "WPS 演示"),
                ],
                default="libreoffice",
                help_text="仅 PPT 源使用；打开放映时可被单次临时选择覆盖。",
                max_length=24,
                verbose_name="PPT 播放器",
            ),
        ),
        migrations.AlterField(
            model_name="playbacksession",
            name="ppt_backend",
            field=models.CharField(
                choices=[
                    ("libreoffice", "LibreOffice（稳定）"),
                    ("powerpoint", "Microsoft PowerPoint"),
                    ("wps", "WPS 演示"),
                ],
                default="libreoffice",
                help_text="记录当前窗口本次 PPT 放映实际使用的播放器。",
                max_length=24,
                verbose_name="当前 PPT 播放器",
            ),
        ),
    ]
