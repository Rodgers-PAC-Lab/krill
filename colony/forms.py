from django import forms

from .models import Mouse, Cage, Person, Gene, MouseGene

from django.utils.safestring import mark_safe

class HorizontalRadioRenderer(forms.RadioSelect.renderer):
    """Arrange the radio select buttons for genotyping horizontally
    
    http://stackoverflow.com/questions/5935546/align-radio-buttons-horizontally-in-django-forms
    
    This hack is currently broken in django 1.11
    But will hopefully be fixed soon
    https://groups.google.com/forum/#!topic/django-users/tlcXfeSVm00
    """
    def render(self):
        return mark_safe(u'\n'.join([u'%s\n' % w for w in self]))

class MatingCageForm(forms.Form):
    """Form for creating a new mating cage"""
    
    mother = forms.ModelChoiceField(label='mother',
        queryset=Mouse.objects.filter(
            sack_date__isnull=True,
            sex=1,
            ).all()
    )
    father = forms.ModelChoiceField(label='father',
        queryset=Mouse.objects.filter(
            sack_date__isnull=True,
            sex=0,
            ).all()
    )
    proprietor = forms.ModelChoiceField(label='proprietor',
        queryset=Person.objects.filter(active=True).all())
    cage_name = forms.CharField(label='cage', max_length=20, required=False,
        help_text=("If you leave this field blank, "
            "it will be auto-generated from the proprietor's name."))

    def clean_cage_name(self):
        data = self.cleaned_data['cage_name']
        if Cage.objects.filter(name=data).count() > 0:
            raise forms.ValidationError("A cage with this name already exists!")
        return data

class SackForm(forms.Form):
   "Form for making cage defunct and sacking its mice" 
   pass 

class WeanForm(forms.Form):
    pass

class AddGenotypingInfoForm(forms.Form):
    """Form for adding genotyping info
    
    Todo: allow setting all mice to the same zygosity at once
    Don't default to +/+ but rather to "---"
    """
    # Dynamically add one results for each pup
    def __init__(self, *args, **kwargs):
        litter = kwargs.pop('litter')
        super(AddGenotypingInfoForm, self).__init__(*args, **kwargs)

        # Identify relevant genes for this litter
        relevant_genes = litter.breeding_cage.relevant_genesets
        try:
            relevant_genes = relevant_genes[0]
        except IndexError:
            # This shouldn't happen
            pass
        
        # Select from the relevant genes
        self.fields['gene_name'] = forms.ModelChoiceField(
            label="Choose the gene that was tested",
            queryset=Gene.objects.filter(name__in=relevant_genes).all(),
        )
        
        # Reorder the choices in order more likely to be clicked
        choices = [(c, c) for c in (
            MouseGene.zygosity_nn,
            MouseGene.zygosity_yn,
            MouseGene.zygosity_yy,
            MouseGene.zygosity_mn,
            MouseGene.zygosity_ym,
            MouseGene.zygosity_mm,
        )]
        
        # Add a field for each mouse
        for mouse in litter.mouse_set.all():
            self.fields['result_%s' % mouse.name] = forms.ChoiceField(
                label="Result for mouse %s" % mouse.name,
                choices=choices,
                widget=forms.RadioSelect(renderer=HorizontalRadioRenderer),
            )

class SetMouseSexForm(forms.Form):
    """Form to set mouse sex on litter management page"""
    # Dynamically add one results for each pup
    def __init__(self, *args, **kwargs):
        litter = kwargs.pop('litter')
        super(SetMouseSexForm, self).__init__(*args, **kwargs)

        # Reorder the choices in order more likely to be clicked
        choices = [
            (2, '?'),
            (0, 'male'),
            (1, 'female'),
        ]
        
        # Add a field for each mouse
        for mouse in litter.mouse_set.all():
            self.fields['sex_%s' % mouse.name] = forms.ChoiceField(
                label="Sex of mouse %s" % mouse.name,
                choices=choices,
                widget=forms.RadioSelect(renderer=HorizontalRadioRenderer),
            )    

class ChangeNumberOfPupsForm(forms.Form):
    number_of_pups = forms.IntegerField(
        label='Number of pups',
    )

class CensusFilterForm(forms.Form):
    """Allows various sorting and filtering of the census"""
    proprietor = forms.ModelChoiceField(
        label='Cage proprietor',
        queryset=Person.objects.filter(active=True).all(),
        required=False,
    )
    
    sort_method = forms.ChoiceField(
        label='Sort by',
        choices=[(c, c) for c in ('cage number', 'rack spot', 'genotype',)]
    )

    include_by_user = forms.BooleanField(
        label="Also include mice by 'user'",
        required=False,
    )
    
    location = forms.ChoiceField(
        label='Location',
        choices=[
            ('All', 'All'),
            (0, '1710'),
            (3, '1736'),
            (4, 'SC2-011'),
            (5, 'L7-057'),
            (6, 'SC2-056'),            
            (7, 'SC2-044'),
        ],
        required=False,
    )
