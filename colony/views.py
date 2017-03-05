from django.shortcuts import render
from django.views import generic
from django.db.models import FieldDoesNotExist
from django.db import IntegrityError
from django.http import HttpResponseRedirect, HttpResponse
import datetime

from .models import (Mouse, Cage, Litter, generate_cage_name,
    get_person_name_from_user_name, Person, get_user_name_from_person_name,
    HistoricalCage, HistoricalMouse, MouseGene, Gene, Genotype)
from .forms import (MatingCageForm, SackForm, AddGenotypingInfoForm,
    ChangeNumberOfPupsForm, CensusFilterForm, WeanForm, SetMouseSexForm)
from simple_history.models import HistoricalRecords
from itertools import chain

import colony.models
import pandas

def counts_by_person(request):
    # Define dates to test
    target_dates = pandas.date_range(
        datetime.date.today() - datetime.timedelta(weeks=20),
        datetime.date.today(), 
        freq='W-WED')[::-1]
    pandas.set_option('display.width', 160)

    pc_l = []
    for target_date in target_dates:
        # Find the most recent historical cage record before target date, distinct
        # by each cage
        qs1 = colony.models.HistoricalCage.objects.filter(
            history_date__lte=target_date).order_by(
            'id', '-history_date').distinct('id')

        # Exclude cages that were defunct at that time
        qs2 = colony.models.HistoricalCage.objects.filter(
            history_id__in=qs1.values_list('history_id', flat=True), defunct=False)

        # Extract proprietor names
        proprietor_names = qs2.values_list('proprietor__name', flat=True)

        # Count them
        proprietor_counts = pandas.Series(list(proprietor_names)).value_counts()

        # Store
        pc_l.append(proprietor_counts)

    # Concat
    df = pandas.concat(pc_l, axis=1).fillna(0).astype(int)
    df.columns = target_dates
    df.ix['total'] = df.sum(0)

    return HttpResponse('<pre>' + str(df) + '</pre>')


def census_by_cage_number(request, census_filter_form, proprietor, 
    include_by_user):
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
    
    # Order by name
    qs = qs.order_by('name')
    
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
        prefetch_related('mouse_set__mousegene_set').\
        prefetch_related('mouse_set__mousegene_set__gene_name').\
        select_related()

    return render(request, 'colony/index.html', {
        'form': census_filter_form,
        'object_list': qs,
        'include_by_user': include_by_user,
    })


def census_by_genotype(request, census_filter_form, proprietor, 
    include_by_user):
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

    # Now select related
    qs = qs.prefetch_related('mouse_set').\
        prefetch_related('specialrequest_set').\
        prefetch_related('specialrequest_set__requester').\
        prefetch_related('specialrequest_set__requestee').\
        prefetch_related('mouse_set__litter').\
        prefetch_related('mouse_set__user').\
        prefetch_related('mouse_set__genotype').\
        prefetch_related('litter__mouse_set').\
        prefetch_related('litter__father__mousegene_set').\
        prefetch_related('litter__mother__mousegene_set').\
        prefetch_related('litter__father__mousegene_set__gene_name').\
        prefetch_related('litter__mother__mousegene_set__gene_name').\
        prefetch_related('mouse_set__mousegene_set').\
        prefetch_related('mouse_set__mousegene_set__gene_name').\
        select_related('litter', 'litter__father', 'litter__mother', 
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
    sort_by = request.GET.get('sort_by', 'cage number')
    include_by_user = request.GET.get('include_by_user', False)
    
    # Get proprietor name
    proprietor = None
    proprietor_name = request.GET.get('proprietor', None)
    
    # Also allow the login name to be specified by the person parameter
    if proprietor_name is None:
        person_name = request.GET.get('person', None)
        proprietor_name = get_person_name_from_user_name(person_name)
    
    # Convert to person object
    if proprietor_name is not None:
        proprietor_qs = Person.objects.filter(name=proprietor_name)
        if proprietor_qs.count() > 0:
            proprietor = proprietor_qs.first()

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
        else:
            # If not valid, I think it returns the same form, and magically
            # inserts the error messages
            pass
    else:
        ## GET, so create a blank form
        # Set up the initial values
        initial = {
            'sort_method': sort_by,
            'proprietor': proprietor,
            'include_by_user': include_by_user,
        }
        census_filter_form = CensusFilterForm(initial=initial)

    # Dispatch to appropriate view, with the form
    if sort_by == 'cage number':
        view = census_by_cage_number
    elif sort_by == 'genotype':
        view = census_by_genotype
    return view(request, census_filter_form=census_filter_form,
        proprietor=proprietor, 
        include_by_user=include_by_user)
    

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
    current_table_data = [{ 
        'name': person.name, 
        'cages': cages.filter(proprietor=person, defunct=False).exclude( 
            mouse__isnull=True).count(),
        'mice': mice.filter(cage__proprietor=person, 
            cage__defunct=False).count(),
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
    form = AddGenotypingInfoForm(initial={}, litter=litter,
        prefix='add_genotyping_info')    
    
    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        ## A POST, so determine which button was pressed
        if 'change_number_of_pups' in request.POST:
            # Make the form with the POST info
            change_number_of_pups_form = ChangeNumberOfPupsForm(
                request.POST, prefix='change_pup')
            
            if change_number_of_pups_form.is_valid():
                # change number of pups
                new_number_of_pups = change_number_of_pups_form.cleaned_data[
                    'number_of_pups']
                
                if new_number_of_pups > litter.mouse_set.count():
                    # Determine the MouseGenes to add
                    mother_genes = list(litter.mother.mousegene_set.values_list(
                        'gene_name__id', flat=True))
                    father_genes = list(litter.father.mousegene_set.values_list(
                        'gene_name__id', flat=True))
                    gene_set = Gene.objects.filter(id__in=(
                        mother_genes + father_genes)).distinct()
                    
                    # pure_breeder if one parent is pure and other is wild
                    pup_is_pure = (
                        (litter.mother.pure_breeder and litter.father.wild_type) or
                        (litter.father.pure_breeder and litter.mother.wild_type))

                    for pupnum in range(litter.mouse_set.count(), new_number_of_pups):
                        # Create a new mouse
                        mouse = Mouse(
                            name='%s-%d' % (litter.breeding_cage.name, pupnum + 1),
                            sex=2,
                            genotype=Genotype.objects.filter(name='TBD').first(),
                            litter=litter,
                            cage=litter.breeding_cage,
                            pure_breeder=pup_is_pure,
                        )
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
                form = AddGenotypingInfoForm(
                    litter=litter, prefix='add_genotyping_info') 
                set_sex_form = SetMouseSexForm(
                    initial={}, litter=litter, prefix='set_sex',
                )
        
        elif 'set_genotyping_info' in request.POST:
            # create a form instance and populate it with data from the request:
            form = AddGenotypingInfoForm(request.POST, 
                initial={}, litter=litter, prefix='add_genotyping_info')
            
            # check whether it's valid:
            if form.is_valid():
                # process the data in form.cleaned_data as required
                gene_name = form.cleaned_data['gene_name']
                for mouse in litter.mouse_set.all():
                    result = form.cleaned_data['result_%s' % mouse.name]
                    
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
                form = AddGenotypingInfoForm(litter=litter, 
                    prefix='add_genotyping_info')
        
        elif 'set_sex' in request.POST:
            ## We are setting the sex of the mice
            # Make the other forms, that we're not processing here
            change_number_of_pups_form = ChangeNumberOfPupsForm(
                prefix='change_pup')   
            form = AddGenotypingInfoForm(
                litter=litter, prefix='add_genotyping_info')   

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

        else:
            # A POST without clicking any submit button
            # (e.g., wrong button name in template)
            # blank forms already created above
            pass

    else:
        ## GET, so create a blank form
        # blank forms already created above
        pass


    return render(request, 'colony/add_genotyping_info.html', 
        {   'form': form, 
            'change_number_of_pups_form': change_number_of_pups_form,
            'set_sex_form': set_sex_form,
            'litter': litter})


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
                cage_name = cage.name + 'M'
                male_cage = colony.models.Cage(
                    name=cage_name,
                    location=cage.location,
                    proprietor=cage.proprietor,
                    notes='',
                )
                male_cage.save()
                for mouse in male_pups.all():
                    mouse.cage = male_cage
                    mouse.save()
            
            # same with females
            if female_pups.count() > 0:
                cage_name = cage.name + 'F'
                female_cage = colony.models.Cage(
                    name=cage_name,
                    location=cage.location,
                    proprietor=cage.proprietor,
                    notes='',
                )
                female_cage.save()
                for mouse in female_pups.all():
                    mouse.cage = female_cage
                    mouse.save()    

            # same with unknown gender
            if unk_pups.count() > 0:
                cage_name = cage.name + 'PUP'
                unk_cage = colony.models.Cage(
                    name=cage_name,
                    location=cage.location,
                    proprietor=cage.proprietor,
                    notes='',
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
