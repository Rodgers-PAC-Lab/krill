from builtins import zip
from django import forms

from .models import Mouse, Cage, Person, Gene, MouseGene

from django.utils.safestring import mark_safe

from dal import autocomplete

#~ class HorizontalRadioSelect(forms.RadioSelect.renderer):
    #~ """Arrange the radio select buttons for genotyping horizontally
    
    #~ http://stackoverflow.com/questions/5935546/align-radio-buttons-horizontally-in-django-forms
    
    #~ This hack is currently broken in django 1.11
    #~ But will hopefully be fixed soon
    #~ https://groups.google.com/forum/#!topic/django-users/tlcXfeSVm00
    #~ """
    #~ def render(self):
        #~ return mark_safe(u'\n'.join([u'%s\n' % w for w in self]))

#~ class HorizontalRadioSelect(forms.RadioSelect):
    #~ # https://stackoverflow.com/questions/5935546/align-radio-buttons-horizontally-in-django-forms
    #~ def __init__(self, *args, **kwargs):
        #~ super().__init__(*args, **kwargs)

        #~ css_style = 'style="display: inline-block; margin-right: 10px;"'

        #~ self.renderer.inner_html = '<li ' + css_style + '>{choice_value}{sub_widgets}</li>'
        
        
class MatingCageForm(forms.Form):
    """Form for creating a new mating cage"""
    
    mother = forms.ModelChoiceField(label='mother',
        queryset=Mouse.objects.filter(
            sack_date__isnull=True,
            sex=1,
            ).all(),
        widget=autocomplete.ModelSelect2(
            url='colony:female-mouse-autocomplete'),
    )
    father = forms.ModelChoiceField(label='father',
        queryset=Mouse.objects.filter(
            sack_date__isnull=True,
            sex=0,
            ).all(),
        widget=autocomplete.ModelSelect2(
            url='colony:male-mouse-autocomplete',
        )
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

#~ # Example of how to use autocomplete
#~ class MouseForm(forms.ModelForm):
    #~ class Meta:
        #~ model = Mouse
        #~ fields = ('__all__')
        #~ widgets = {
            #~ 'manual_father': autocomplete.ModelSelect2(url='colony:mouse-autocomplete'),
            #~ 'manual_mother': autocomplete.ModelSelect2(url='colony:mouse-autocomplete'),
        #~ }

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


        ## Identify the relevant genes to include on the drop-down
        # This code is copy-pasted from the relevant_genesets property
        # on Cage. There is a weird edge case where, if the mother only
        # was moved out of the cage, it will no longer show up as a 
        # breeding cage and relevant_genesets will be incorrect. Instead,
        # directly grab the relevant genes here.
        gene_name_res = []
        gene_type_res = []
        for parent in [litter.father, litter.mother]:
            for mg in parent.mousegene_set.all():
                if mg.gene_name.name not in gene_name_res:
                    gene_name_res.append(mg.gene_name.name)
                    gene_type_res.append(mg.gene_name.gene_type)
        
        # Sort the gene names by the gene types
        sorted_gene_names = [gene_name for gene_type, gene_name in 
            sorted(zip(gene_type_res, gene_name_res))]
        
        
        ## Now create the form fields
        # Select from the relevant genes
        self.fields['gene_name'] = forms.ModelChoiceField(
            label="Choose the gene that was tested",
            queryset=Gene.objects.filter(name__in=sorted_gene_names).all(),
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
                #~ widget=HorizontalRadioSelect,
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
                #~ widget=HorizontalRadioSelect,
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
            (8, 'L5-036'),
        ],
        required=False,
    )
