from django.shortcuts import render
from django.views import generic
from django.db.models import FieldDoesNotExist
from django.http import HttpResponseRedirect
import datetime

from .models import  Mouse, Cage, Litter
from .forms import MatingCageForm

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
        
        'order_by' can be passed as a query parameter
        
        TODO: also apply to user field of mouse, and special request
        field.
        
        TODO: Link this to the Person class, to account for usernames
        that don't exactly match Person names. Right now we're using
        'proprietor_name_icontains', which works for 'Amanda/Georgia',
        but wouldn't work for names that are subsets of other names.
        """
        # could also do:
        # pname = self.request.user.username
        pname = self.request.GET.get('person')
        order_by = self.request.GET.get('order_by', 'name')
        
        # ensure order_by is valid
        # this fucks up ordering by -column_name
        # so disregard this check and let the user enter it correctly
        # http://stackoverflow.com/questions/7173856/django-order-by-fielderror-exception-can-not-be-catched
        #~ try:
            #~ Cage._meta.get_field_by_name(order_by)
        #~ except FieldDoesNotExist:
            #~ order_by = None
        
        qs = Cage.objects
        
        # First filter
        if pname:
            qs = qs.filter(proprietor__name__icontains=pname) 
        
        # Now order
        if order_by:
            # What if order_by == 'name'?
            qs = qs.order_by(order_by, 'name')
        
        return qs

def make_mating_cage(request):
    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = MatingCageForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            # process the data in form.cleaned_data as required
            # ...
            # redirect to a new URL:
            father = form.cleaned_data['father']
            mother = form.cleaned_data['mother']
            cage_name = form.cleaned_data['cage_name']
            proprietor = form.cleaned_data['proprietor']
            
            cage = Cage(
                name=cage_name,
                proprietor=proprietor,
            )
            cage.save()

            litter = Litter(
                breeding_cage=cage,
                proprietor=proprietor,
                father=father,
                mother=mother,
                date_mated=datetime.date.today(),
            )
            

            mother.cage = cage
            father.cage = cage
            
            
            litter.save()
            mother.save()
            father.save()
            
            
            return HttpResponseRedirect('/admin/colony/cage/%d' % cage.pk)

    # if a GET (or any other method) we'll create a blank form
    else:
        form = MatingCageForm()

    return render(request, 'colony/new_mating_cage.html', {'form': form})