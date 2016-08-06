from django.conf.urls import url

from . import views

app_name = 'colony'
urlpatterns = [
    url(r'^$', views.IndexView.as_view(), name='index'),
    url(r'^cages/$', views.cages, name='cages'),
]