from django.conf.urls import url
from django.contrib.auth.decorators import login_required

from . import views

app_name = 'colony'
urlpatterns = [
    url(r'^$', login_required(views.IndexView.as_view()), name='index'),
    url(r'^new_mating_cage$', login_required(views.make_mating_cage), name='new_mating_cage'),
    url(r'^summary$', login_required(views.summary), name='summary'),
    url(r'^records$', login_required(views.records), name='records'),
]