from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('illit/', views.illit_page, name='illit'),
    path('api/query/', views.query, name='query'),
    path('api/history/', views.history, name='history'),
    path('api/history/<int:record_id>/', views.delete_record, name='delete'),
    path('api/posts/', views.post_list, name='posts'),
    path('api/crawl/', views.crawl, name='crawl'),
    path('api/crawl/', views.crawl, name='crawl'),
]