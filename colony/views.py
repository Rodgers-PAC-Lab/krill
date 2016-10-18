from django.shortcuts import render
from django.views import generic
from django.db.models import FieldDoesNotExist
from django.http import HttpResponseRedirect
import datetime

from .models import (Mouse, Cage, Litter, generate_cage_name,
    get_person_name_from_user_name, Person, get_user_name_from_person_name)
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
        
        qs = Cage.objects.filter(defunct=False)
        
        # First filter
        if pname:
            qs = qs.filter(proprietor__name__icontains=pname) 
        
        # Now order
        if order_by:
            # What if order_by == 'name'?
            qs = qs.order_by(order_by, 'name')
        
        return qs

def make_mating_cage(request):
    """View for making a new mating cage.
    
    We create a MatingCageForm and pass it the logged-in user.
    If the data is valid, we create a new Cage object, insert the
    father and mother, and create a new Litter object with those
    mice as parents.
    
    If the cage name is not specified, it is auto-generated from the
    proprietor's name.
    """
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
            
            # Define the cage name
            if cage_name == '':
                user_name = get_user_name_from_person_name(str(proprietor.name))
                cage_name = generate_cage_name(user_name)
            
            # Create the cage
            cage = Cage(
                name=cage_name,
                proprietor=proprietor,
            )
            cage.save()

            # Create the litter
            litter = Litter(
                breeding_cage=cage,
                proprietor=proprietor,
                father=father,
                mother=mother,
                date_mated=datetime.date.today(),
            )
            
            # Put mice in this cage and save everything
            mother.cage = cage
            father.cage = cage
            litter.save()
            mother.save()
            father.save()
            
            # Redirect to admin change page
            return HttpResponseRedirect('/admin/colony/cage/%d' % cage.pk)

    # if a GET (or any other method) we'll create a blank form
    else:
        person_name = get_person_name_from_user_name(str(request.user))
        person = Person.objects.filter(name=person_name).first()
        initial = {
            'proprietor': person,
        }
        form = MatingCageForm(initial=initial)

    return render(request, 'colony/new_mating_cage.html', {'form': form})


def summary(request):
    persons = Person.objects.all()
    mice = Mouse.objects.all()
    cages = Cage.objects.all()

    #Contains information about all cages and mice stored in databse
    all_table_data = [{ 'name': person.name, 
                    'cages': cages.filter(proprietor=person).count(),
                    'mice': mice.filter(user=person).count(),
                } for person in persons]
    all_totals = {'cages' : Cage.objects.count(), 'mice' : Mouse.objects.count()}
    #Contains information about only non-defunct cages and non-sacked mice
    current_table_data = [{ 'name': person.name, 
                    'cages': len([cage for cage in cages.filter(proprietor=person, defunct=False) if not cage.defunct]),
                    'mice': len([mouse for mouse in mice.filter(user=person) if not mouse.sacked]),
                } for person in persons]

    current_totals = {'cages' : Cage.objects.filter(defunct=False).count(), 'mice' : len([mouse for mouse in Mouse.objects.all() if not mouse.sacked])}

    #Totals do not match column totals yet

    return render(request, 'colony/summary.html', {'persons_all': all_table_data, 'persons_current': current_table_data,
                                                    'all_totals': all_totals,
                                                    'current_totals' : current_totals,
                                                    })



