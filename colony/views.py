from django.shortcuts import render
from django.views import generic
from django.db.models import FieldDoesNotExist
from django.http import HttpResponseRedirect
import datetime

from .models import (Mouse, Cage, Litter, generate_cage_name,
    get_person_name_from_user_name, Person, get_user_name_from_person_name,
    HistoricalCage, HistoricalMouse)
from .forms import MatingCageForm

from simple_history.models import HistoricalRecords
from itertools import chain

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
        
        # Now select related
        qs = qs.prefetch_related('mouse_set').\
            prefetch_related('specialrequest_set').\
            prefetch_related('specialrequest_set__requester').\
            prefetch_related('specialrequest_set__requestee').\
            prefetch_related('mouse_set__litter').\
            prefetch_related('mouse_set__user').\
            prefetch_related('mouse_set__genotype').\
            prefetch_related('litter').\
            prefetch_related('litter__mouse_set').\
            prefetch_related('litter__father').\
            prefetch_related('litter__mother').\
            select_related()
        
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
    """Returns cage and mouse counts by person for a summary view
    
    For this summary, we use the "proprietor" attribute of cage to determine
    who owns it. We use cage__proprietor to determine who owns a mouse. This
    is because mouse.user is usually null. Note that this will fail when a
    mouse has no cage (typically after sacking). These mice are listed as
    belonging to "No Cage".
    
    Would probably be better to use the "user_or_proprietor" property
    of Mouse, but this is Python (not a slug) so would be too slow here.
    
    'persons_all':
        list of dicts, each with keys:
            'name': each person's name
            'cages': number of cages for which that person is proprietor
            'mice': number of mice in those cages
    
    'persons_current':
        Same as above, but only for cages for which defunct=False.
    """
    persons = Person.objects.all()
    mice = Mouse.objects.all()
    cages = Cage.objects.all()

    # Contains information about all cages and mice stored in databse
    all_table_data = [{ 
        'name': person.name, 
        'cages': cages.filter(proprietor=person).count(),
        'mice': mice.filter(cage__proprietor=person).count(),
    } for person in persons]
    
    # Add entry for mice without a cage
    all_table_data.append({
        'name': 'No Cage',
        'cages': 0,
        'mice': mice.filter(cage__isnull=True).count()
    })
    all_totals = {'cages' : sum([person['cages'] for person in all_table_data]), 
        'mice' : sum([person['mice'] for person in all_table_data])}

    # Contains information about only non-defunct cages
    current_table_data = [{ 
        'name': person.name, 
        'cages': cages.filter(proprietor=person, defunct=False).count(),
        'mice': mice.filter(cage__proprietor=person, 
            cage__defunct=False).count(),
    } for person in persons]


    current_totals = {'cages' : sum([person['cages'] for person in current_table_data]),
        'mice' : sum([person['mice'] for person in current_table_data])}


    return render(request, 'colony/summary.html', {
        'persons_all': all_table_data, 
        'persons_current': current_table_data,
        'all_totals' : all_totals,
        'current_totals' : current_totals,
    })

def records(request):
    mouse_records = Mouse.history.all()
    cage_records = Cage.history.all()

    #Merge the historical mouse and cage records
    records = sorted(chain(mouse_records, cage_records),
        key=lambda instance: instance.history_date, reverse=True)


    #Take at most 50 records
    records = records[:50] if len(records) > 50 else records[:len(records)]

    rec_summaries = []

    for i in range(len(records)):
        new_record = records[i]
        old_record = new_record.get_previous_by_history_date()

        #Find which fields differ between the 2 records
        old_fields, new_fields = compare(new_record, old_record)
        # statement = new_record.history_date.strftime('%Y-%m-%d %H:%M-%S') + "\t"
        model = ''

        if type(new_record) == HistoricalCage:
            model = 'Cage'
        elif type(new_record) == HistoricalMouse:
            model = 'Mouse'

        name = model + ' ' + new_record.name
        alter_time = new_record.history_date.strftime('%Y-%m-%d %H:%M-%S')
        changes = []


        for j, field in enumerate(old_fields.keys()):
            # clause = "Changed {} from '{}' to '{}'".format(field, old_fields[field], new_fields[field])

            # statement += clause

            # if j == len(old_fields) - 1:
            #     statement += ",  "
            # else:
            #     statement += "."

            old = old_fields[field]
            new = new_fields[field]
            change_type = 'change'


            if not old:
                change_type = 'addition'
            elif not new:
                change_type = 'removal'


            changes.append({
                'field' : field.capitalize(),
                'old' : old_fields[field],
                'new' : new_fields[field],
                'type' : change_type, 
            })

        rec_summary = {
            'name' : name,
            'alter_time' : alter_time,
            'changes' : changes,
        }


        rec_summaries.append(rec_summary)



        

    return render(request, 'colony/records.html', {
        'rec_summaries' : rec_summaries
        })

def compare(obj1,obj2):
    excluded_keys = ('created', '_state', 'timestamp', 'user', 'uid', 'changed',
        'history_id', 'history_date', 'history_user_id', 'history_type', 'id')
    return _compare(obj1, obj2, excluded_keys)

def _compare(obj1, obj2, excluded_keys):
    d1, d2 = obj1.__dict__, obj2.__dict__
    old, new = {}, {}
    for k,v in d1.items():
        if k in excluded_keys:
            continue
        try:
            if v != d2[k]:
                old.update({k: v})
                new.update({k: d2[k]})
        except KeyError:
            old.update({k: v})
    
    return old, new  



