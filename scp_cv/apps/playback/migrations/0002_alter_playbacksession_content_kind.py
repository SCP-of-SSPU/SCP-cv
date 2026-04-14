# Generated manually — choices label 由 "SRT 流" 更新为 "WebRTC 流"

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('playback', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='playbacksession',
            name='content_kind',
            field=models.CharField(
                choices=[('none', '无'), ('stream', 'WebRTC 流')],
                default='none',
                max_length=16,
            ),
        ),
    ]
