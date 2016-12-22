from django import forms

from .models import Mouse, Cage, Person, Gene, MouseGene


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
        queryset=Person.objects.all())
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



class AddGenotypingInfoForm(forms.Form):
    """Form for adding genotyping info
    
    Todo: allow setting all mice to the same zygosity at once
    Don't default to +/+ but rather to "---"
    """
    # Dynamically add one results for each pup
    def __init__(self, *args, **kwargs):
        litter = kwargs.pop('litter')
        super(AddGenotypingInfoForm, self).__init__(*args, **kwargs)
        
        # Create a choices that includes ---
        choices = list(MouseGene.zygosity_choices_dbl)
        choices.insert(0, ('', '---'))
        
        for mouse in litter.mouse_set.all():
            self.fields['result_%s' % mouse.name] = forms.ChoiceField(
                label="Result for mouse %s" % mouse.name,
                choices=choices,
            )
    
    gene_name = forms.ModelChoiceField(
        label="Choose the gene that was tested",
        queryset=Gene.objects.all(),
    )
    
class ChangeNumberOfPupsForm(forms.Form):
    number_of_pups = forms.IntegerField(
        label='Number of pups',
    )
