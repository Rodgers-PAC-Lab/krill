from django.urls import re_path
from django.contrib.auth.decorators import login_required

from . import views

app_name = 'colony'
urlpatterns = [
    re_path(r'^$', login_required(views.census), name='index'),
    re_path(r'^census$', login_required(views.census), name='census'),
    re_path(r'^census_by_genotype$', login_required(views.census_by_genotype), name='census_by_genotype'),
    re_path(r'^new_mating_cage$', login_required(views.make_mating_cage), name='new_mating_cage'),
    re_path(r'^add_genotyping_info/([0-9]+)/$', login_required(views.add_genotyping_information), name='add_genotyping_info'),
    re_path(r'^summary$', login_required(views.summary), name='summary'),
    re_path(r'^records$', login_required(views.records), name='records'),
    re_path(r'^counts_by_person$', login_required(views.counts_by_person), name='counts_by_person'),
    re_path(r'^sack/([0-9]+)/$', login_required(views.sack), name='sack'),
    re_path(r'^wean/([0-9]+)/$', login_required(views.wean), name='wean'),
    re_path(r'^mouse-autocomplete/$', 
        login_required(views.MouseAutocomplete.as_view()), 
        name='mouse-autocomplete',),
    re_path(r'^unsacked-mouse-autocomplete/$', 
        login_required(views.UnsackedMouseAutocomplete.as_view()), 
        name='unsacked-mouse-autocomplete',),            
    re_path(r'^female-mouse-autocomplete/$', 
        login_required(views.FemaleMouseAutocomplete.as_view()), 
        name='female-mouse-autocomplete',),
    re_path(r'^male-mouse-autocomplete/$', 
        login_required(views.MaleMouseAutocomplete.as_view()), 
        name='male-mouse-autocomplete',),        
]