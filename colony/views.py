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
        """Return cages relating to a certain user.
        
        'person' can be passed as a query parameter
        For now this is applied to the proprietor field of the cage.
        
        TODO: also apply to user field of mouse, and special request
        field.
        
        TODO: Link this to the Person class, to account for usernames
        that don't exactly match Person names. Right now we're using
        'proprietor_name_icontains', which works for 'Amanda/Georgia',
        but wouldn't work for names that are subsets of other names.
        """
        pname = self.request.GET.get('person')
        
        # could also do:
        # pname = self.request.user.username
        
        if pname:
            return Cage.objects.order_by('name').filter(
                proprietor__name__icontains=pname) 
        else:
            return Cage.objects.order_by('name').all()

