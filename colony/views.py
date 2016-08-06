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

def cages(request):
    """Return view of cages for django_tables2
    
    This has basically been replaced by the IndexView above.
    """
    return render(request, 'colony/cages.html', {'cages': Cage.objects.order_by('-name').all()})

#~ class MouseDetailView(generic.ListView):
    #~ model = Mouse
    #~ template_name = 'colony/mouse_detail.html'

#~ class CageDetailView(generic.ListView):
    #~ model = Cage
    #~ template_name = 'colony/cage_detail.html'