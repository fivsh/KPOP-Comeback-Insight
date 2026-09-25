from django.db import models

class QueryRecord(models.Model):
    question = models.TextField(verbose_name='用户问题')
    answer = models.TextField(verbose_name='AI回答')
    source = models.CharField(max_length=50, default='ai', verbose_name='信息来源')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'query_records'
        ordering = ['-created_at']


class Post(models.Model):
    platform = models.CharField(max_length=20)
    title = models.CharField(max_length=500)
    author = models.CharField(max_length=100)
    view_count = models.IntegerField(default=0)
    likes = models.IntegerField(default=0)
    phase = models.CharField(max_length=20)
    publish_time = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'posts'
        managed = False  # Scrapy 管理表结构，Django 只读