from django.conf.urls import url
from django.contrib.auth.decorators import login_required

from . import views

app_name = 'colony'
urlpatterns = [
    url(r'^$', login_required(views.census), name='index'),
    url(r'^census$', login_required(views.census), name='census'),
    url(r'^census_by_genotype$', login_required(views.census_by_genotype), name='census_by_genotype'),
    url(r'^new_mating_cage$', login_required(views.make_mating_cage), name='new_mating_cage'),
    url(r'^add_genotyping_info/([0-9]+)/$', login_required(views.add_genotyping_information), name='add_genotyping_info'),
    url(r'^summary$', login_required(views.summary), name='summary'),
    url(r'^records$', login_required(views.records), name='records'),
    url(r'^sack/([0-9]+)/$', login_required(views.sack), name='sack'),
]