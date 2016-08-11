from django.shortcuts import render
from django.views import generic

from .models import  Mouse, Cage

# Create your views here.

class IndexView(generic.ListView):
    """Returns all cages sorted by name for the CensusView to display
    
    See the template in templates/colony/index.html
    """
    template_name = 'colony/index.html'
    model = Cage
    def get_queryset(self):
        return Cage.objects.order_by('name').all()
