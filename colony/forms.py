from django import forms

from .models import Mouse, Cage, Person


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
   pass 



