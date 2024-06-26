from builtins import str
from builtins import range
from django.shortcuts import render
from django.views import generic
from django.core.exceptions import FieldDoesNotExist
from django.db import IntegrityError
from django.http import HttpResponseRedirect, HttpResponse
import datetime

from .models import (Mouse, Cage, Litter, generate_cage_name,
    Person,
    have_same_single_gene,
    HistoricalCage, HistoricalMouse, MouseGene, Gene, Genotype,
    Strain, MouseStrain)
from .forms import (MatingCageForm, SackForm, AddGenotypingInfoForm,
    ChangeNumberOfPupsForm, CensusFilterForm, WeanForm, SetMouseSexForm, SetMouseToesForm)
from simple_history.models import HistoricalRecords
from itertools import chain

# I think there's a thread problem with importing pyplot here
# Maybe if you specify matplotlib.use('Agg') it would be okay
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure

import colony.models
import pandas

from dal import autocomplete
from colony.models import Mouse


## Autocomplete views
# https://django-autocomplete-light.readthedocs.io/en/master/tutorial.html
# I can't figure how to use forward filtering in this version of dal
# so separate ones for each
class MouseAutocomplete(autocomplete.Select2QuerySetView):
    """Autocomplete for all mice"""
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Mouse.objects.none()

        qs = Mouse.objects.all()

        if self.q:
            qs = qs.filter(name__istartswith=self.q)

        return qs        

class UnsackedMouseAutocomplete(autocomplete.Select2QuerySetView):
    """Autocomplete for unsacked mice"""
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Mouse.objects.none()

        qs = Mouse.objects.filter(sack_date__isnull=True).all()

        if self.q:
            qs = qs.filter(name__istartswith=self.q)

        return qs      

# These two are for mating cage
class FemaleMouseAutocomplete(autocomplete.Select2QuerySetView):
    """Autocomplete for unsacked female mice"""
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Mouse.objects.none()

        qs = Mouse.objects.filter(sex=1, sack_date__isnull=True).all()

        sex = self.forwarded.get('sex', None)
        if sex:
            qs = qs.filter(sex=sex)

        if self.q:
            qs = qs.filter(name__istartswith=self.q)

        return qs       

class MaleMouseAutocomplete(autocomplete.Select2QuerySetView):
    """Autocomplete for unsacked male mice"""
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Mouse.objects.none()

        qs = Mouse.objects.filter(sex=0, sack_date__isnull=True).all()

        if self.q:
            qs = qs.filter(name__istartswith=self.q)

        return qs       


def counts_by_person(request):
    # Define dates to test (for graphing)
    target_dates = pandas.date_range(
        datetime.date.today() - datetime.timedelta(weeks=20),
        datetime.date.today(), 
        tz='America/New_York',
        freq='D')[::-1]
    
    # Dates to test (tabular output)
    tabular_target_dates = pandas.date_range(
        datetime.date.today() - datetime.timedelta(weeks=20),
        datetime.date.today(), 
        tz='America/New_York',
        freq='W-WED')[::-1]


    ## Iterate over target_dates
    pc_l = []
    for target_date in target_dates:
        # Find the most recent historical cage record before target date, 
        # distinct by each cage
        qs1 = colony.models.HistoricalCage.objects.filter(
            history_date__lte=target_date).order_by(
            'id', '-history_date').distinct('id')

        # Include only cages that were non-defunct and in 1710 at that time
        # And also exclude any deleted cages
        # I think cages that contained no mice are also included here
        qs2 = colony.models.HistoricalCage.objects.filter(
            history_id__in=qs1.values_list('history_id', flat=True), 
            defunct=False, location__in=[0, 4]).exclude(history_type='-')

        # Extract proprietor names
        proprietor_names = qs2.values_list('proprietor__name', flat=True)

        # Count them
        proprietor_counts = pandas.Series(list(proprietor_names)).value_counts()

        # Store
        pc_l.append(proprietor_counts)

    # Concat
    df = pandas.concat(pc_l, axis=1, sort=True).fillna(0).astype(int)
    df.columns = target_dates
    
    # Sort by usage
    df = df.loc[df.sum(1).sort_values().index[::-1]]
    
    # Add a total
    df.loc['total'] = df.sum(0)


    ## Repeat everything above for tabular
    tabular_pc_l = []
    for target_date in tabular_target_dates:
        # Find the most recent historical cage record before target date, 
        # distinct by each cage
        qs1 = colony.models.HistoricalCage.objects.filter(
            history_date__lte=target_date).order_by(
            'id', '-history_date').distinct('id')

        # Include only cages that were non-defunct and in 1710 at that time
        # And also exclude any deleted cages
        # I think cages that contained no mice are also included here
        qs2 = colony.models.HistoricalCage.objects.filter(
            history_id__in=qs1.values_list('history_id', flat=True), 
            defunct=False, location__in=[0, 4]).exclude(history_type='-')

        # Extract proprietor names
        proprietor_names = qs2.values_list('proprietor__name', flat=True)

        # Count them
        proprietor_counts = pandas.Series(list(proprietor_names)).value_counts()

        # Store
        tabular_pc_l.append(proprietor_counts)

    # Concat
    tabular_df = pandas.concat(tabular_pc_l, axis=1, sort=True).fillna(0).astype(int)
    tabular_df.columns = tabular_target_dates
    
    # Sort by usage
    tabular_df = tabular_df.loc[tabular_df.sum(1).sort_values().index[::-1]]
    
    # Add a total
    tabular_df.loc['total'] = tabular_df.sum(0)    
    
    
    ## Format tabular text
    # Concatenate every 6 days of tabular data
    pandas.set_option('display.width', 160)
    string_result = ''
    for idx in range(0, len(tabular_target_dates), 5):
        subdf = tabular_df.iloc[:, idx:idx+5]
        string_result += str(subdf) + '\n\n'
    
    # Format in pre tags
    string_result = '<pre>' + string_result + '</pre>'


    ## Plot
    # Extract only people with enough cages
    subdf = df.loc[
        (df.mean(1) > 5) |
        (df.iloc[:, 0] > 5)
    ]

    # Create the figure
    f = Figure(figsize=(10, 7))
    f.subplots_adjust(right=.85)
    ax = f.add_subplot(1, 1, 1)

    
    # Always plot total first
    if 'total' in subdf.index:
        subdf = subdf.drop('total')
    ax.plot(df.loc['total'], color='k', label='total')
    
    # Now plot the rest
    ax.plot(subdf.T)
    
    # Pretty
    ax.grid()
    ax.set_xlabel('date')
    ax.set_ylabel('number of cages')
    
    # Legend
    ax.legend(['total'] + list(subdf.index), loc='center left', bbox_to_anchor=(1, 0.5))
    
    # Title
    ax.set_title('cage counts in 1710 and SC2-011')
    #~ ax.set_xticklabels(ax.get_xticks(), rotation=90)

    # Print
    # This is just to directly display it
    #~ canvas = FigureCanvas(f)
    #~ response = HttpResponse(content_type='image/png')
    #~ canvas.print_png(response)
    
    # Put it into an img tag
    # http://stackoverflow.com/questions/31492525/converting-matplotlib-png-to-base64-for-viewing-in-html-template
    from io import BytesIO
    import base64
    figfile = BytesIO()
    canvas = FigureCanvas(f)
    canvas.print_png(figfile)
    figfile.seek(0)
    figdata_png = base64.b64encode(figfile.getvalue()).decode('utf-8')
    img_result = '<img src="data:image/png;base64,%s"\\>' % figdata_png
    
    
    ## Return both
    response = HttpResponse(img_result + string_result)
    return response



def census_by_cage_number(request, census_filter_form, proprietor, 
    include_by_user, location='All', order_by='name'):
    """View for displaying by cage number
    
    Usually dispatched from census
    """
    # Get all non-defunct cages
    qs = Cage.objects.filter(defunct=False)
    
    # Filter by proprietor
    if proprietor is not None:
        # could also do:
        # pname = self.request.user.username
        
        # Cages owned by proprietor
        qs = qs.filter(proprietor=proprietor) 
    
        if include_by_user:
            # Mice with this user who are not sacked
            mice_id_l = Mouse.objects.filter(
                user=proprietor, sack_date__isnull=True).values_list(
                'cage__id', flat=True)
            
            # Cages containing mice with this user
            user_cages_qs = Cage.objects.filter(id__in=mice_id_l, defunct=False)
            
            # Full qs is the union
            qs = qs | user_cages_qs
    
    # Filter by location
    if location != 'All':
        qs = qs.filter(location=location)
    
    # Order by name
    qs = qs.order_by(order_by)
    
    # Now select related
    # I used to also prefetch_related on mouse_set__genotype but this
    # stopped working
    qs = qs.prefetch_related('mouse_set').\
        prefetch_related('specialrequest_set').\
        prefetch_related('specialrequest_set__requester').\
        prefetch_related('specialrequest_set__requestee').\
        prefetch_related('mouse_set__litter').\
        prefetch_related('mouse_set__user').\
        prefetch_related('litter__mouse_set').\
        prefetch_related('litter__father__mousegene_set').\
        prefetch_related('litter__mother__mousegene_set').\
        prefetch_related('litter__father__mousegene_set__gene_name').\
        prefetch_related('litter__mother__mousegene_set__gene_name').\
        prefetch_related('mouse_set__mousegene_set').\
        prefetch_related('mouse_set__mousegene_set__gene_name').\
        select_related('litter', 'litter__father', 'litter__mother', 
            'litter__mother__cage', # for contains_mother_of_this_litter
            'proprietor', 'litter__proprietor')

    return render(request, 'colony/index.html', {
        'form': census_filter_form,
        'object_list': qs,
        'include_by_user': include_by_user,
    })


def census_by_genotype(request, census_filter_form, proprietor, 
    include_by_user, location='All'):
    """View cages sorted by genotype
    
    Usually dispatched from census
    sorted_by_geneset is added to context
    """
    # Get all non-defunct cages
    qs = Cage.objects.filter(defunct=False)    

    # Filter by proprietor
    if proprietor is not None:
        qs = qs.filter(proprietor=proprietor) 

        if include_by_user:
            # Mice with this user who are not sacked
            mice_id_l = Mouse.objects.filter(
                user=proprietor, sack_date__isnull=True).values_list(
                'cage__id', flat=True)
            
            # Cages containing mice with this user
            user_cages_qs = Cage.objects.filter(id__in=mice_id_l, defunct=False)
            
            # Full qs is the union
            qs = qs | user_cages_qs

    # Filter by location
    if location != 'All':
        qs = qs.filter(location=location)

    # Now select related
    # I used to also prefetch_related on mouse_set__genotype but this
    # stopped working    
    qs = qs.prefetch_related('mouse_set').\
        prefetch_related('specialrequest_set').\
        prefetch_related('specialrequest_set__requester').\
        prefetch_related('specialrequest_set__requestee').\
        prefetch_related('mouse_set__litter').\
        prefetch_related('mouse_set__user').\
        prefetch_related('litter__mouse_set').\
        prefetch_related('litter__father__mousegene_set').\
        prefetch_related('litter__mother__mousegene_set').\
        prefetch_related('litter__father__mousegene_set__gene_name').\
        prefetch_related('litter__mother__mousegene_set__gene_name').\
        prefetch_related('mouse_set__mousegene_set').\
        prefetch_related('mouse_set__mousegene_set__gene_name').\
        select_related('litter', 'litter__father', 'litter__mother', 
            'litter__mother__cage', # for contains_mother_of_this_litter
            'proprietor', 'litter__proprietor')

    # Extract relevant genesets
    relevant_genesets = [cage.relevant_genesets for cage in qs.all()]
    unique_relevant_genesets = []
    for rg in relevant_genesets:
        for srg in rg:
            tsrg = tuple(srg)
            if tsrg not in unique_relevant_genesets:
                unique_relevant_genesets.append(tsrg)
    
    # Sort by first gene, then number of genes
    unique_relevant_genesets = sorted(unique_relevant_genesets, 
        key=lambda v: (v[0] if len(v) > 0 else '', len(v)))

    # Should remove this second iteration over qs.all() for SQL efficiency
    # Just iterate once and save everything necessary
    #
    # Iterate once over cages and group by geneset
    geneset2cage_l = {}
    for cage in qs.all():
        for geneset in cage.relevant_genesets:
            if geneset in geneset2cage_l:
                geneset2cage_l[geneset].append(cage)
            else:
                geneset2cage_l[geneset] = [cage]

    # Now refactor
    sorted_by_geneset = []
    for geneset in unique_relevant_genesets:
        sorted_by_geneset.append({
            'geneset': geneset,
            'dname': (' x '.join(geneset)) if len(geneset) > 0 else 'WT',
            'cage_l': geneset2cage_l[geneset]
        })

    return render(request, 'colony/census_by_genotype.html', {
        'form': census_filter_form,
        'sorted_by_geneset': sorted_by_geneset,
    })

def census(request):
    """Display cages and option for sorting or filtering
    
    This also handles all getting of GET parameters
    """
    # Default values for form parameters
    # I think this location actualy determine the initial queryset
    sort_by = request.GET.get('sort_by', 'cage number')
    include_by_user = request.GET.get('include_by_user', False)
    location = request.GET.get('location', 'All')
    
    # Get proprietor to filter by
    # This can be the 'proprietor' parameter, matching on proprietor.name
    # or the 'person' parameter, matching on proprietor.login_name
    proprietor_name = request.GET.get('proprietor', None)
    login_name = request.GET.get('person', None)
    
    # Filter first by proprietor name and secondly by login name
    if proprietor_name is not None:
        proprietor_qs = Person.objects.filter(name=proprietor_name)
    elif login_name is not None:
        proprietor_qs = Person.objects.filter(login_name=login_name)
    else:
        proprietor_qs = None
    
    # Resolve to a single person if possible
    if proprietor_qs is not None and proprietor_qs.count() > 0:
        proprietor = proprietor_qs.first()    
    else:
        proprietor = None

    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # Make the form with the POST info
        census_filter_form = CensusFilterForm(request.POST)
        
        if census_filter_form.is_valid():
            # Set the new sort method if it was chosen
            sort_by = census_filter_form.cleaned_data['sort_method']
            
            # Set other parameters
            proprietor = census_filter_form.cleaned_data['proprietor']
            include_by_user = census_filter_form.cleaned_data[
                'include_by_user']
            location = census_filter_form.cleaned_data[
                'location']
        else:
            # If not valid, I think it returns the same form, and magically
            # inserts the error messages
            pass
    else:
        ## GET, so create a blank form
        # Set up the initial values
        # I think this only determines what goes in the form widgets,
        # not the actual sorting
        initial = {
            'sort_method': sort_by,
            'proprietor': proprietor,
            'include_by_user': include_by_user,
            'location': location,
        }
        census_filter_form = CensusFilterForm(initial=initial)

    # Dispatch to appropriate view, with the form
    if sort_by == 'cage number':
        # The normal view, ordered by name by default
        view = census_by_cage_number
        kwargs = {}
    elif sort_by == 'rack spot':
        # The normal view, but a custom order_by
        view = census_by_cage_number
        kwargs = {'order_by': 'rack_spot'}
    elif sort_by == 'genotype':
        # The genotype view
        view = census_by_genotype
        kwargs = {}
    else:
        raise ValueError("unknown sort_by: %r" % sort_by)
    
    return view(request, census_filter_form=census_filter_form,
        proprietor=proprietor, 
        include_by_user=include_by_user,
        location=location,
        **kwargs
    )

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
                series_number = proprietor.series_number
                cage_name = generate_cage_name(series_number)
            
            # Create the cage
            cage = Cage(
                name=cage_name,
                proprietor=proprietor,
            )
            cage.save()

            # Get the dob of the mother's last litter to use as the mating date for the new cage.
            prev_litters = colony.models.Litter.objects.filter(mother=mother)
            if prev_litters.exists():
                # Excludes mothers with no previous litters at all
                if prev_litters.filter(dob__isnull=False).filter(father=father).exists():
                    # If the previous litter was from the same parents,
                    # assume the mating date is dob of the previous litter
                    previous_dob = prev_litters.filter(dob__isnull=False).filter(father=father).latest("dob").dob
                    date_mated = previous_dob
                else:
                    date_mated = datetime.date.today()
            #           print("catch 1")
            else:
                # If there are no previous litters, date_mated is today.
                date_mated = datetime.date.today()

            # Create the litter
            litter = Litter(
                breeding_cage=cage,
                proprietor=proprietor,
                father=father,
                mother=mother,
                date_mated= date_mated,
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
        # Find matching Person by login name
        person_qs = Person.objects.filter(login_name=str(request.user))
        if person_qs.count() > 0:
            person = person_qs.first()
        else:
            person = None

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

    # Contains information about all cages and mice stored in database
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
    all_totals = {
        'cages' : sum([person['cages'] for person in all_table_data]), 
        'mice' : sum([person['mice'] for person in all_table_data])}

    # Contains information about only non-defunct cages
    # Exclude empty cages
    # Include only cages in 1710
    current_table_data = [{ 
        'name': person.name, 
        'cages': cages.filter(
            proprietor=person, defunct=False, location__in=[0, 4]).exclude( 
            mouse__isnull=True).count(),
        'mice': mice.filter(cage__proprietor=person, 
            cage__defunct=False, cage__location__in=[0, 4]).count(),
    } for person in persons]

    current_totals = {
        'cages' : sum([person['cages'] for person in current_table_data]),
        'mice' : sum([person['mice'] for person in current_table_data])}

    return render(request, 'colony/summary.html', {
        'persons_all': all_table_data, 
        'persons_current': current_table_data,
        'all_totals' : all_totals,
        'current_totals' : current_totals,
    })

def records(request):
    """ Returns a feed of Mouse and Cage model change
    
    The historical record object is used to obtain the previous 50 model changes
    and identify which fields are altered in each
    
    Returns a request with "rec_summaries" in context data.
    rec_summaries is a list in chronological order.
    Each entry is a dict with the following fields:
        name: string with format
            "%MODEL_NAME% %NEW_OBJECT_NAME% %HISTORY_TYPE%"
        alter_time: time it was changed
        changes: list of changes to this object.
            Each entry in 'changes' is a dict with fields:
            field : name of field that was changed
            old: previous value
            new: new value
            type: 'addition', 'removal', or 'change'
        
    """
    # get some filters from the URL
    proprietor = request.GET.get('proprietor')
    n_records = request.GET.get('n')
    try:
        n_records = int(n_records)
    except TypeError:
        n_records = 50
    
    # Get all historical mouses and historical cages
    mouse_records = Mouse.history
    cage_records = Cage.history
    if proprietor:
        mouse_records = mouse_records.filter(
            cage__proprietor__name__icontains=proprietor)
        cage_records = cage_records.filter(
            proprietor__name__icontains=proprietor)

    # Merge the historical mouse and cage records
    records = sorted(chain(mouse_records.all(), cage_records.all()),
        key=lambda instance: instance.history_date, reverse=True)

    # Take at most 50 records
    records = records[:n_records]
    
    # Exclude these fields
    exclude_fields = ['history_date', 'history_id', 'history_user',
        'history_type']

    # Summarize each change
    rec_summaries = []
    for new_record in records:
        ## First get the model name
        if type(new_record) == HistoricalCage:
            model = 'Cage'
        elif type(new_record) == HistoricalMouse:
            model = 'Mouse'
        else:
            raise ValueError("unknown model type")        
        
        ## Get the previous version of this object, for comparison
        # This is the pk of the object that was changed
        real_object_pk = new_record.instance.pk
        
        # Search for earlier historical objects with the same pk
        change_datetime = new_record.history_date
        hrecs_same_object = new_record.__class__.objects.filter(
            id=real_object_pk, 
            history_date__lt=change_datetime)
        
        # Take the most recent one that is before this one
        old_record = hrecs_same_object.order_by('history_date').last()

        ## Store some metadata
        rec_summary = {
            'model': model,
            'name': new_record.name,
            'history_type': new_record.history_type,
            'history_user': str(new_record.history_user),
            'alter_time': new_record.history_date.strftime('%Y-%m-%d %H:%M-%S'),
        }

        ## Compare old and new records, if possible
        if old_record is None:
            # No previous record to compare with
            assert new_record.history_type == '+'
            rec_summary['changes'] = []
        else:
            ## Find which fields differ between the 2 records
            old_fields = type(old_record)._meta.get_fields()
            new_fields = type(new_record)._meta.get_fields()
            
            # Identify which are present in the old but not the new
            for field in old_fields:
                # This will raise AttributeError if not present
                getattr(new_record, field.name)
            
            # Iterate over all fields in the new
            changes = []
            for field in new_fields:
                # Skip if excluded
                fieldname = field.name
                if fieldname in exclude_fields:
                    continue
                
                # Get the old and new field values
                # This will raise AttributeError if not present in old
                old_field_value = getattr(old_record, fieldname)
                new_field_value = getattr(new_record, fieldname)
                change = {
                    'field': fieldname,
                    'old': old_field_value,
                    'new': new_field_value,
                }
                
                # Determine if this was added, deleted, changed, or nothing
                if old_field_value is None and new_field_value is not None:
                    change['type'] = 'addition'
                elif new_field_value is None and old_field_value is not None:
                    change['type'] = 'removal'
                elif old_field_value != new_field_value:
                    change['type'] = 'change'
                else:
                    # no change made to this field
                    continue
                
                # Append change, if any
                changes.append(change)

            # Store in rec_summary and append
            rec_summary['changes'] = changes
        rec_summaries.append(rec_summary)

    return render(request, 'colony/records.html', {
        'rec_summaries' : rec_summaries
    })

def sack(request, cage_id):
    """Sack all mice in the cage and mark the cage as defunct"""
    cage = Cage.objects.get(pk=cage_id)
    mice = Mouse.objects.filter(cage=cage)

    #If the form is being submitted
    if request.method == 'POST':
        form = SackForm(request.POST)

        if form.is_valid():
            #Make all cage/mice defunct
            cage.defunct = True
            cage.save()
            for mouse in mice:
                mouse.sack_date = datetime.date.today()
                mouse.save()
            
            #redirect to census
            return HttpResponseRedirect('/colony/') 

    return render(request, 'colony/sack.html', {
        'cage' : cage,
        'mice' : mice,

    })

def add_genotyping_information(request, litter_id):
    """A view with multiple forms for managing litter.
    
    Forms:
    * Button for setting number of pups
    * Form to enter genotyping result for each mouse
    * Form to set the sex of each mouse
    * Button to wean the litter
    
    Blank forms are created for each. If a submit button was pressed,
    a new form is created with the POST data and the result is processed.
    """
    litter = Litter.objects.get(pk=litter_id)
    
    ## Create blank instances of each form
    # These will be replaced below if the litter object has changed,
    # or if they need to be populated with POST data
    change_number_of_pups_form = ChangeNumberOfPupsForm(
        initial={}, prefix='change_pup',
    )
    set_sex_form = SetMouseSexForm(
        initial={}, litter=litter, prefix='set_sex',
    )
    set_toes_form = SetMouseToesForm(
        initial={}, litter=litter, prefix='set_toes',
    )
    genotyping_form = AddGenotypingInfoForm(initial={}, litter=litter,
        prefix='add_genotyping_info')    
    
    
    ## Depends on the request method
    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        ## A POST, so determine which button was pressed
        if 'change_number_of_pups' in request.POST:
            # Need to redo all forms in order to change number of pups
            genotyping_form, change_number_of_pups_form, set_sex_form, set_toes_form = (
                post_change_number_of_pups(request, litter))
        
        elif 'set_genotyping_info' in request.POST:
            # For this we only need to redo the set_genotyping form
            genotyping_form = post_set_genotyping_info(request, litter)
        
        elif 'set_sex' in request.POST:
            # For this we only need to redo the set sex form
            set_sex_form = post_set_sex(request, litter)
        elif 'set_toes' in request.POST:
            # For this we only need to redo the set toe form
            set_toes_form = post_set_toes(request, litter)
        else:
            # A POST without clicking any submit button
            # (e.g., wrong button name in template)
            # blank forms already created above
            pass

    else:
        ## GET, so create a blank form
        # blank forms already created above
        pass

    
    ## Render and return
    render_kwargs = {   
        'form': genotyping_form, 
        'change_number_of_pups_form': change_number_of_pups_form,
        'set_sex_form': set_sex_form,
        'set_toes_form': set_toes_form,
        'litter': litter}

    return render(request, 'colony/add_genotyping_info.html', render_kwargs)

def post_change_number_of_pups(request, litter):
    """Called when POST with change_number_of_pups.
    
    Creates pups based on parents' strain and genotype.
    Regenerates forms and returns.
    """
    # Make the form with the POST info
    change_number_of_pups_form = ChangeNumberOfPupsForm(
        request.POST, prefix='change_pup')

    if change_number_of_pups_form.is_valid():
        # change number of pups
        new_number_of_pups = change_number_of_pups_form.cleaned_data[
            'number_of_pups']
        
        if new_number_of_pups > litter.mouse_set.count():
            add_pups_to_litter(litter, new_number_of_pups)
        
        elif new_number_of_pups < litter.mouse_set.count():
            # Delete unneeded pups
            # Assume the pup numbering is correct, so if we want
            # to go from 6 to 4, delete 5 and 6
            for pupnum in range(new_number_of_pups, litter.mouse_set.count()):
                # Find the matching pup
                mouse_name = '%s-%d' % (
                    litter.breeding_cage.name, pupnum + 1)
                mouse = Mouse.objects.filter(name=mouse_name)
                
                # Delete, but do nothing if we didn't find any pups
                if mouse.count() == 1:
                    mouse.delete()

        # Remake the forms that depend on litter with the POST data
        genotyping_form = AddGenotypingInfoForm(
            litter=litter, prefix='add_genotyping_info') 
        set_sex_form = SetMouseSexForm(
            initial={}, litter=litter, prefix='set_sex',
        )
        set_toes_form = SetMouseToesForm(
            initial={}, litter=litter, prefix='set_toes',
        )
    
    return genotyping_form, change_number_of_pups_form, set_sex_form, set_toes_form

def post_set_genotyping_info(request, litter):
    """Called when POST with set_genotyping_info.
    
    Sets genotypes and generates the form.
    """    
    # create a form instance and populate it with data from the request:
    genotyping_form = AddGenotypingInfoForm(request.POST, 
        initial={}, litter=litter, prefix='add_genotyping_info')
    
    # check whether it's valid:
    if genotyping_form.is_valid():
        # process the data in form.cleaned_data as required
        gene_name = genotyping_form.cleaned_data['gene_name']
        for mouse in litter.mouse_set.all():
            result = genotyping_form.cleaned_data['result_%s' % mouse.name]
            
            # If the mouse gene already exists, change it
            mgqs = MouseGene.objects.filter(
                mouse_name=mouse, gene_name=gene_name)
            
            if mgqs.count() == 0:
                # Create it
                mg = MouseGene(
                    gene_name=gene_name,
                    mouse_name=mouse,
                    zygosity=result,
                )
                mg.save()
            else:
                # Edit it
                mg = mgqs.first()
                mg.zygosity = result
                mg.save()
        
        # Create a new, blank form (so the fields default to blank
        # rather than to the values we just entered)
        genotyping_form = AddGenotypingInfoForm(litter=litter, 
            prefix='add_genotyping_info')
    
    return genotyping_form

def post_set_sex(request, litter):
    """Called when POST with set sex.
    
    Sets the sex and generates the form.
    """
    ## We are setting the sex of the mice
    # create a form instance and populate it with data from the request:
    set_sex_form = SetMouseSexForm(request.POST, 
        initial={}, litter=litter, prefix='set_sex')            
    
    # Process if valid
    if set_sex_form.is_valid():
        # Set the sex of each submitted mouse
        for mouse in litter.mouse_set.all():
            sex = set_sex_form.cleaned_data['sex_%s' % mouse.name]
            mouse.sex = sex
            mouse.save()
    
    return set_sex_form
def post_set_toes(request, litter):
    """Called when POST with set toes.

    Sets the clipped toes and generates the form.
    """
    ## We are setting the clipped toes of the mice
    # create a form instance and populate it with data from the request:
    set_toes_form = SetMouseToesForm(request.POST,
                                   initial={}, litter=litter, prefix='set_toes')

    # Process if valid
    if set_toes_form.is_valid():
        # Set the sex of each submitted mouse
        for mouse in litter.mouse_set.all():
            toe = set_toes_form.cleaned_data['toe_clipped_%s' % mouse.name]
            mouse.toe_clipped = toe
            mouse.save()

    return set_toes_form
def add_pups_to_litter(litter, new_number_of_pups):
    """Calculates strains and genotypes, and adds pups to litter"""
    # Get strains of progeny
    strains, strains_weight = get_strain_of_progeny(litter)
    if len(strains) == 1:
        mother_and_father_same_single_strain = True
    else:
        mother_and_father_same_single_strain = False
    
    # Determine the MouseGenes to add
    mother_genes = list(litter.mother.mousegene_set.values_list(
        'gene_name__id', flat=True))
    father_genes = list(litter.father.mousegene_set.values_list(
        'gene_name__id', flat=True))
    gene_set = Gene.objects.filter(id__in=(
        mother_genes + father_genes)).distinct()
    
    # pure_breeder if one parent is pure and other is wild
    # or if both are pure breeders of the same gene
    # But always only if they are the same strain
    pup_is_pure = ((
        (litter.mother.pure_breeder and litter.father.pure_wild_type) or
        (litter.father.pure_breeder and litter.mother.pure_wild_type) or
        (litter.father.pure_breeder and 
        litter.mother.pure_breeder and
        have_same_single_gene(litter.mother, litter.father))) and
        mother_and_father_same_single_strain
    )
    
    # pure_wild_type if both parents are wild_type
    # and both parents are same strain
    pup_is_pure_wild_type = (
        litter.mother.pure_wild_type and litter.father.pure_wild_type and
        mother_and_father_same_single_strain
    )
    
    # pure_wild_type implies pure_breeder
    if pup_is_pure_wild_type:
        pup_is_pure = True

    # Add each pup in turn
    for pupnum in range(litter.mouse_set.count(), new_number_of_pups):
        # Create a new mouse
        mouse = Mouse(
            name='%s-%d' % (litter.breeding_cage.name, pupnum + 1),
            sex=2,
            litter=litter,
            cage=litter.breeding_cage,
            pure_breeder=pup_is_pure,
            pure_wild_type=pup_is_pure_wild_type,
        )
        
        # Try to save
        try:
            mouse.save()
        except IntegrityError:
            # Mouse already exists due to naming the pups weirdly
            continue
        
        # Add its genes
        for gene in gene_set:
            mg = MouseGene(mouse_name=mouse, gene_name=gene,
                zygosity='?/?')
            mg.save()
        
        # Add its strains
        for strain, weight in zip(strains, strains_weight):
            ms = MouseStrain(
                mouse_key=mouse, strain_key=strain, 
                weight=weight)
            ms.save()    

def get_strain_of_progeny(litter):
    """Calculate the strain of the progeny of a litter"""
    # construct the new strain set
    mother_strain = list(
        litter.mother.mousestrain_set.values_list('strain_key__id', 'weight'))
    father_strain = list(
        litter.father.mousestrain_set.values_list('strain_key__id', 'weight'))
    
    # Depends how many strains there are
    if len(mother_strain) == 0 or len(father_strain) == 0:
        # If either has the strain unspecified, no way to know
        strains = []
        strains_weight = []
    elif len(mother_strain) == 1 and len(father_strain) == 1:
        # The parents are single strain, not hybrids
        mother_strain_id, mother_strain_weight = mother_strain[0]
        father_strain_id, father_strain_weight = father_strain[0]
        
        # Depends if they are the same strain
        if mother_strain_id == father_strain_id:
            # Mother and father are same strain, so so is the progeny
            strains = [Strain.objects.filter(id=mother_strain_id).first()]
            strains_weight = [1]
        
        else:
            # Mother and father are different strain, so 
            # progeny will be 1:1
            strains = [
                Strain.objects.filter(id=mother_strain_id).first(),
                Strain.objects.filter(id=father_strain_id).first(),
                ]
            strains_weight = [1, 1]
    else:
        # unsupported
        raise ValueError("cannot deal with breeding hybrids")
    
    return strains, strains_weight

def wean(request, cage_id):
    """Wean pups in the cage's litter into new cages"""
    cage = Cage.objects.get(pk=cage_id)
    male_pups = cage.litter.mouse_set.filter(sex=0).all()
    female_pups = cage.litter.mouse_set.filter(sex=1).all()
    unk_pups = cage.litter.mouse_set.filter(sex=2).all()

    #If the form is being submitted
    if request.method == 'POST':
        form = WeanForm(request.POST)

        if form.is_valid():
            # Create the cages and move the mice
            if male_pups.count() > 0:
                cage_name = cage.name + '-M'
                male_cage = colony.models.Cage(
                    name=cage_name,
                    location=cage.location,
                    proprietor=cage.proprietor,
                    notes='',
                    dar_type=2, # weaning type
                )
                male_cage.save()
                for mouse in male_pups.all():
                    mouse.cage = male_cage
                    mouse.save()
            
            # same with females
            if female_pups.count() > 0:
                cage_name = cage.name + '-F'
                female_cage = colony.models.Cage(
                    name=cage_name,
                    location=cage.location,
                    proprietor=cage.proprietor,
                    notes='',
                    dar_type=2, # weaning type
                )
                female_cage.save()
                for mouse in female_pups.all():
                    mouse.cage = female_cage
                    mouse.save()    

            # same with unknown gender
            if unk_pups.count() > 0:
                cage_name = cage.name + '-PUP'
                unk_cage = colony.models.Cage(
                    name=cage_name,
                    location=cage.location,
                    proprietor=cage.proprietor,
                    notes='',
                    dar_type=2, # weaning type
                )
                unk_cage.save()
                for mouse in unk_pups.all():
                    mouse.cage = unk_cage
                    mouse.save()    
            
            cage.litter.date_weaned = datetime.date.today()
            cage.litter.save()


            ## Redirect to a new mating cage form for the parents
            # Should redirect to a new mating cage form, or do that above
            # For now just redirect to the litter maintenance page
            return HttpResponseRedirect('/colony/')

    return render(request, 'colony/wean.html', {
        'cage' : cage,
        'male_pups' : male_pups,
        'female_pups' : female_pups,
        'unk_pups' : unk_pups,
    })

def current_litters(request):
    """View for cages that need to be weaned
    
    This view returns an HttpResponse containing metadata about all litters
    that have been born but not weaned, and are not from a defunct
    breeding cage. This metadata is displayed in a table with the following 
    headings:
        'Cage', 'Sticker', 'DoBirth', 'Early wean', 'Late wean', 
        'Sexual maturity'

    Arguments:
        request : not used
    
    Returns: HttpResponse
        This response contains the table described above.
    """
    # Find all Litter objects that are not weaned and are not from
    # defunct cages
    breeding = colony.models.Litter.objects.filter(
        date_weaned=None, breeding_cage__defunct=False)
    
    # This queryset includes only those Litter that have been born
    born = breeding.exclude(dob=None)
    
    
    # Helper function
    def get_weaning_dates():
        """Return data about each litter in `born`.
        
        Returns : list, of the same length as `born`
            Each entry is a tuple containing data about that litter
                breeding_cage
                sticker
                DOB
                earliest wean date
                latest wean date
                maturity date
        """
        # Keep track of weaning data here
        weaning_data = []
        
        # Iterate over all litters that have been born but not weaned
        for x in born:
            # Get the sticker for the cage of the same name
            sticker = colony.models.Cage.objects.filter(name=x)[0].sticker
            
            # Identify the earliest and latest possible wean dates
            earliest_wean = x.dob + datetime.timedelta(days=19)
            latest_wean = x.dob + datetime.timedelta(days=24)
            
            # Identify the time of maturity for this cage
            maturity = x.dob + datetime.timedelta(days=7*5)
            
            # Store breeding_cage, sticker name, DOB, and the three dates above
            results = (
                x.breeding_cage, sticker, x.dob, 
                earliest_wean, latest_wean, maturity,
                )
            weaning_data.append(results)
        
        return weaning_data
    
    # Get the data about each litter in `born`
    weaning_data = get_weaning_dates()
    
    # Convert this data to a DataFrame
    wean_tbl = pandas.DataFrame(weaning_data,
        columns=[
            'Cage', 'Sticker', 'DoBirth', 
            'Early wean', 'Late wean', 'Sexual maturity',
            ]
        )
    wean_tbl = wean_tbl.set_index('Cage')
    
    # Convert the table to HTML
    wean_test = wean_tbl.to_html()
    
    # Write the table into an HttpResponse
    response = HttpResponse('<h2>Litters born, waiting to wean</h2>')
    response.write(wean_test)
    
    # Add a TODO note at the end
    response.write(
        '<p>To do: add a table for weaned litters needing a sex check</p>'
        '<p>Add a table for breeding pairs waiting on litters and dates to '
        'start checking for pups</p>')
    
    return response
