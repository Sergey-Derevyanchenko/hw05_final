# Generated by Django 2.2.16 on 2022-05-05 11:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0005_auto_20220505_1445'),
    ]

    operations = [
        migrations.AlterField(
            model_name='post',
            name='image',
            field=models.ImageField(blank=True, help_text='Изображение', upload_to='posts/', verbose_name='Картинка'),
        ),
    ]
