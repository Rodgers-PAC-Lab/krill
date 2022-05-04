from builtins import str
from builtins import object
from django.contrib import admin
from .models import (Mouse, Genotype, Litter, 
    Cage, Person, SpecialRequest, HistoricalMouse, Gene, MouseGene)
# Register your models here.
from django.db.models import Count
from django.urls import reverse
from simple_history.admin import SimpleHistoryAdmin
from django.contrib.admin.views.main import ChangeList
from django.utils.safestring import mark_safe
from django import forms
from dal import autocomplete

class GenotypedFilter(admin.SimpleListFilter):
    """Filter by whether the genotype date is null or not
    
    https://www.elements.nl/2015/03/16/getting-the-most-out-of-django-admin-filters/
    """
    title = 'Genotyped'
    parameter_name = 'date_genotyped' # not sure this does anything
    
    def lookups(self, request, model_admin):
        """Map the choice strings in the URL to human-readable text
        
        Note that an "All" choice is always presented, but we're breaking
        it, so we need no provide an "Actually All".
        """
        return(
            ('yes', 'yes'),
            ('no', 'no'),
            ('all', 'Actually All'),
        )
        
    def queryset(self, request, queryset):
        filter_value = self.value()
        if filter_value == 'no':
            return queryset.filter(date_genotyped__isnull=True)
        elif filter_value == 'yes':
            return queryset.filter(date_genotyped__isnull=False)
        elif filter_value == 'all':
            return queryset
        else:
            raise ValueError("unexpected value %s" % filter_value)
    
    def value(self):
        """Override value() to be 'no' by default
        
        Bug here because selecting the hardwired "All" option will still
        choose 'no'.
        """
        value = super(GenotypedFilter, self).value()
        if value is None:
            value = 'no'
        return value

class GeneAdmin(admin.ModelAdmin):
    list_display = ('name', 'gene_type',)

class MouseGeneInline(admin.TabularInline):
    """Displayed within Mouse, for adding genotyping information"""
    model = MouseGene
    extra = 0

class LitterInline(admin.StackedInline):
    """For adding a Litter to a Cage"""
    model = Litter
    extra = 0
    show_change_link = True
    
    # These nested inlines are no longer used
    #~ inlines = [MouseInline]#, MouseGeneInline,]
    readonly_fields = ('link_to_management_page',)

    # Disable the ability to delete from the Cage page, because this
    # is an easy mistake to make (and won't even go to delete confirmation
    # page)
    def has_delete_permission(self, request, obj=None):
        return False

    # We need access to obj.management_link, so have to put it in this
    # function
    @mark_safe
    def link_to_management_page(self, obj):
        """Generate link to litter management page"""
        link_html_code = u'<a href="%s">%s</a><br />' % (
            obj.management_link, 'Litter management page')
        return link_html_code
    link_to_management_page.allow_tags = True        
    link_to_management_page.short_description = 'Litter management page'

    
    # The purpose of this fieldset is simply to display help text above
    # the Mouse Pup inline, but then we have to explicitly declare all
    # the other fields above it
    fieldsets = (
        (None, {
            'fields': (
                'proprietor', 'father', 'mother', 'date_mated', 'dob',
                'date_toeclipped', 'date_weaned', 'date_checked',
                'date_genotyped',
                'notes',
            ),
            #~ 'description': 'Help text goes here',
        }),
        (None, {
            'fields': ('link_to_management_page',),
            'description': (
                '<font size="3">To add pups, provide sex or genotyping ' + 
                'information, or wean, go to the litter management page</font>'),
        }),
    )
    
class SpecialRequestInline(admin.TabularInline):
    model = SpecialRequest
    extra = 1
    show_change_link = True
    inlines = []

class LitterAdminChangeList(ChangeList):
    """Override the Litter changelist to go to Cage instead"""
    def url_for_result(self, result):
        """Clicking the Litter name takes you to the cage page"""
        pk = result.breeding_cage.pk
        return '/admin/colony/cage/%d' % pk

class LitterAdmin(admin.ModelAdmin):
    """View for identifying litters that need to be genotyped"""
    list_display = ('name', 'dob', 'date_toeclipped', 'cross', 'info',
        'get_special_request_message', 'cage_notes', 'notes', 'date_genotyped',)
    #~ inlines = [MouseInline] 
    list_editable = ('notes', 'date_genotyped', 'date_toeclipped',)
    list_filter = ('breeding_cage__proprietor', GenotypedFilter)
    readonly_fields = ('target_genotype', 'info', 'cross', 'age', 
        'get_special_request_message', 'name',)
    
    # Order first by date_genotyped (in case we are viewing the
    # ones that have already been genotyped)
    # then by dob and date_toeclipped (in case we are viewing the ones
    # that haven't been genotyped yet)
    ordering = ('-date_genotyped', 'dob', 'date_toeclipped', 
        'breeding_cage__name',)

    def get_changelist(self, request, **kwargs):
        """Overrule changelist so that clicking litter name goes to page"""
        return LitterAdminChangeList

    def get_queryset(self, request):
        """Only return litters that are born."""
        qs = super(LitterAdmin, self).get_queryset(request)
        return qs.filter(dob__isnull=False)

    def name(self, obj):
        return str(obj)

    @mark_safe
    def get_special_request_message(self, obj):
        return obj.breeding_cage.get_special_request_message()
    get_special_request_message.allow_tags = True
    get_special_request_message.short_description = 'Requests'

    def cage_notes(self, obj):
        return obj.breeding_cage.notes

    def cross(self, obj):
        return obj.breeding_cage.printable_relevant_genesets
    cross.short_description = 'Cross'
    
    def n_pups(self, obj):
        return obj.mouse_set.count()
    n_pups.short_description = 'Size'

class DefunctFilter(admin.SimpleListFilter):
    """By default, filter by defunct=False
    
    https://www.elements.nl/2015/03/16/getting-the-most-out-of-django-admin-filters/
    """
    title = 'whether the cage is defunct'
    parameter_name = 'defunct'
    
    def lookups(self, request, model_admin):
        """Map the choice strings in the URL to human-readable text
        
        Note that an "All" choice is always presented, but we're breaking
        it, so we need no provide an "Actually All".
        """
        return (
            ('no', 'Active'),
            ('yes', 'Defunct'),
            ('all', 'Actually All'),
        )
    
    def queryset(self, request, queryset):
        """Filter by the selected self.value()"""
        filter_value = self.value()
        if filter_value == 'no':
            return queryset.filter(defunct=False)
        elif filter_value == 'yes':
            return queryset.filter(defunct=True)
        elif filter_value == 'all':
            return queryset
        else:
            raise ValueError("unexpected value %s" % filter_value)
    
    def value(self):
        """Override value() to be 'no' by default
        
        Bug here because selecting the hardwired "All" option will still
        choose 'no'.
        """
        value = super(DefunctFilter, self).value()
        if value is None:
            value = 'no'
        return value

class AddMiceToCageForm(forms.ModelForm):
    """Special form to allow adding mice from the cage admin page.
    
    Basically we just add a ModelMultipleChoiceField, populated with
    the current mouse set. Upon saving, we update the cage field on
    each mouse.
    
    References:
    Adapted from here: http://stackoverflow.com/questions/6034047/one-to-many-inline-select-with-django-admin
    See also: http://stackoverflow.com/questions/17948018/django-admin-add-custom-form-fields-that-are-not-part-of-the-model
    The trick of adding fields = '__all__' comes from the second link
    """
    # http://stackoverflow.com/questions/6034047/one-to-many-inline-select-with-django-admin
    class Meta(object):
        model = Cage
        
        # Without this, complains that fields or exclude needs to be set
        fields = '__all__'
    
    # Custom form field for selecting multiple mice
    #~ add_mouse_to_cage = forms.ModelChoiceField(required=False,
        #~ queryset=Mouse.objects.filter(sack_date__isnull=True).all())

    # New version using autocomplete
    add_mouse_to_cage = forms.ModelChoiceField(
        required=False,
        queryset=Mouse.objects.filter(sack_date__isnull=True).all(),
        widget=autocomplete.ModelSelect2(
            url='colony:unsacked-mouse-autocomplete'),
    )
    
    # Override __init__ if you want to specify initial
    
    def save(self, commit=True, *args, **kwargs):
        """Add the selected mouse to this cage.
        
        Sets the selected mouse's cage attribute to this cage.
        commit argument is not handled
        
        This seems to correctly save the "add_mouse_to_cage" form
        field only if a mouse was actually selected.
        """
        # Call the superclass save function but don't commit
        # Not even sure what this does other than set up `instance`
        instance = super(AddMiceToCageForm, self).save(commit=False)

        # Get the selected mouse, if any
        selected_mouse = self.cleaned_data['add_mouse_to_cage']
        
        if selected_mouse:        
            # Set the selected mouse's cage attribute to this cage
            selected_mouse.cage = instance
            
            # Save it, in order to trigger any custom save stuff
            # (important for historical mouse records)
            selected_mouse.save()
        
        return instance        

class CageAdmin(admin.ModelAdmin):
    """Admin page for the Cage object.

    A custom form is used to allow adding mice using multiple
    selection, as opposed to individually going to each mouse page.
    """
    # Columns in the list page
    list_display = ('name', 'rack_spot', 'proprietor', 
        'target_genotype', 'link_to_mice', 
        'auto_needs_message', 'notes',)
    
    # The ones that are editable
    list_editable = ('notes', 'rack_spot',)
    
    # This allows filtering by proprietor name and defunctness
    # Also filter by genotype of contained mice
    list_filter = ('proprietor__name', DefunctFilter, 
        'mouse__mousegene__gene_name', 'location',)
    
    # Allow searching cages by mouse info
    # Searching by litter__target_genotype allows us to include relevant
    # breeding cages even if the father is out of the picture.
    search_fields = ('name', 
        'mouse__name', 'litter__target_genotype', 
        'mouse__mousegene__gene_name__name')
    
    # Sorting in the list page
    ordering = ('defunct', 'name',)
    
    # The readonly fields
    readonly_fields = ('infos', 'target_genotype', 
        'link_to_mice', 'auto_needs_message', #'litter__target_genotype',
        'target_genotype')
    
    # Litter is an inline
    inlines = [LitterInline, SpecialRequestInline]

    # A special form for adding mice
    form = AddMiceToCageForm

    # Pagination to save time
    list_per_page = 20

    ## Define what shows up on the individual cage admin page
    # Clickable links to every mouse in the cage
    @mark_safe
    def link_to_mice(self, obj):
        """Generate HTML links for every mouse in the cage"""
        link_html_code = ''
        for child in obj.mouse_set.order_by('name').all():
            child_link = reverse("admin:colony_mouse_change", 
                args=[child.id])
            child_info = child.info()
            if child_info is None or child_info == '':
                child_info = 'mouse'
            link_html_code += u'<a href="%s">%s</a><br />' % (
                child_link, child_info)
        return link_html_code
    link_to_mice.allow_tags = True        
    link_to_mice.short_description = 'Mice in this cage'
    
    # Arrangement of fields on individual cage admin page
    fieldsets = (
        (None, {
            'fields': (
                'name', 'defunct', 'location', 'proprietor', 'dar_type',),
            'description': 'Required properties',
        }),
        (None, {
            'fields': (
                'rack_spot', 'notes', 'dar_id', 'color', 'dar_req_num',),
            'description': 'Optional properties',
        }),        
        (None, {
            'fields': ('link_to_mice', 'add_mouse_to_cage',),
            'description': 'Mice currently in this cage, and option to add more',
        }),                     
        (None, {
            'fields': ('target_genotype', 'auto_needs_message',),
            'description': 'Litter husbandry information',
        }),
    )

    
    # Override the width of the charfield for rack_spot
    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == 'rack_spot':
            kwargs['widget'] = forms.TextInput(attrs={'size': '8'})
        return super(CageAdmin, self).formfield_for_dbfield(db_field, **kwargs)

    # This affects all charfields
    #~ formfield_overrides = {
        #~ django.db.models.CharField: {
            #~ 'widget': forms.TextInput(attrs={'size': '20'})}
    #~ }


class SackFilter(admin.SimpleListFilter):
    title = 'Sacked'
    parameter_name = 'sac date'
    
    def lookups(self, request, model_admin):
            return(
                ('yes', 'yes'),
                ('no', 'no'),
            )
        
    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(sack_date__isnull=False)
        
        if self.value() == 'no':
            return queryset.filter(sack_date__isnull=True)

class MouseAdmin(admin.ModelAdmin):
    """Mouse administration: list view and individual admin page"""
    ## List view for mice
    # The columns that show up
    list_display = ('name', 'user', 'dob', 'age', 'sacked', 'sex', 'cage', 
        'genotype', 'notes',)
    list_editable = ('notes',)
    readonly_fields = ('info', 'age', 'dob', 'mother', 'father', 'sacked', 
        'link_to_mother', 'link_to_father', 'link_to_progeny',
        'link_to_cage', 'cage_history_string', 'litter_management',
        'old_genotype', 'genotype',)

    # How to filter and search
    list_filter = ['cage__proprietor', 'user', 'pure_breeder', SackFilter, 
        'mousegene__gene_name',
    ]
    search_fields = ('name', 'mousegene__gene_name__name')
    
    # How it is sorted by default
    ordering = ('name',)
    
    # Pagination to save time
    list_per_page = 20

    ## Ordering for choosing cage for mouse
    # http://stackoverflow.com/questions/8992865/django-admin-sort-foreign-key-field-list
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # Would like to exclude defunct cages here but I think people are
        # moving mice to defunct cages
        if db_field.name == "cage":
            kwargs["queryset"] = Cage.objects.order_by('name')
        return super(MouseAdmin, self).formfield_for_foreignkey(
            db_field, request, **kwargs)

    ## Create fields that are HTML links to other mice
    # http://stackoverflow.com/questions/28832897/link-in-django-admin-to-foreign-key-object
    @mark_safe
    def link_to_mother(self, obj):
        link = reverse("admin:colony_mouse_change", 
            args=[obj.mother.id])
        return u'<a href="%s">%s</a>' % (link, obj.mother.name)
    link_to_mother.allow_tags=True    
    
    @mark_safe
    def link_to_father(self, obj):
        link = reverse("admin:colony_mouse_change", 
            args=[obj.father.id])
        return u'<a href="%s">%s</a>' % (link, obj.father.name)
    link_to_father.allow_tags=True    

    @mark_safe
    def link_to_cage(self, obj):
        link = reverse("admin:colony_cage_change", 
            args=[obj.cage.id])
        return u'<a href="%s">%s</a>' % (link, obj.cage.name)
    link_to_cage.allow_tags=True    

    @mark_safe
    def link_to_progeny(self, obj):
        """Generate HTML links for every child"""
        link_html_code = ''
        for child in obj.progeny:
            child_link = reverse("admin:colony_mouse_change", 
                args=[child.id])
            child_info = child.info()
            if child_info is None or child_info == '':
                child_info = 'pup'
            link_html_code += u'<a href="%s">%s</a><br />' % (
                child_link, child_info)
        return link_html_code
    link_to_progeny.allow_tags=True    

    @mark_safe
    def litter_management(self, obj):
        """Generate link to litter management page"""
        link_html_code = u'<a href="%s">%s</a><br />' % (
            obj.litter.management_link, 'Litter management page')
        return link_html_code
    litter_management.allow_tags = True        

    # Shortcuts to display read-only genotype
    def old_genotype(self, obj):
        return obj.genotype
    old_genotype.short_description = 'Old genotype (historical mice only)'
    
    def genotype(self, obj):
        return obj.genotype
    genotype.short_description = 'Genotype'

    ## Individual Mouse admin page
    fieldsets = (
        (None, {
            'fields': ('name', 'sex',),
            'description': 'Required properties',
        }),
        (None, {
            'fields': ('cage', 'link_to_cage', 'sack_date', 
                'user', 'notes',),
            'description': 'Optional properties',
        }),        
        (None, {
            'fields': ('genotype', 'pure_breeder', 'pure_wild_type', 
                'litter_management', 'old_genotype',),
            'description': 'Genotyping',
        }),             
        (None, {
            'fields': ('link_to_mother', 'link_to_father', 'link_to_progeny',),
            'description': 'Genealogy',
        }),     
        (None, {
            'fields': ('cage_history_string', ),
            'description': 'Historical cage records',
        }),                
        (None, {
            'fields': ('dob', 'age', 'manual_father', 'manual_mother', 'manual_dob',),
            'description': (
                'These properties are normally derived from the litter. '
                'Override mother, father, and DOB here if necessary.'),
        }),        
            (None, {
            'fields': (),
            'description': (
                'Add a gene for a newly acquired pure breeder here. ' +
                'For progeny mice, genotyping info should instead be added ' + 
                'using the "litter management page" linked above.')
        }),    
    )
    
    # Inlines for adding mouse genes
    inlines = [MouseGeneInline,]

    # Override the mouse chooser widget
    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == 'manual_father':
            kwargs['widget'] = autocomplete.ModelSelect2(
                url='colony:mouse-autocomplete')
        elif db_field.name == 'manual_mother':
            kwargs['widget'] = autocomplete.ModelSelect2(
                url='colony:mouse-autocomplete')
        return super(MouseAdmin, self).formfield_for_dbfield(db_field, **kwargs)

    
class MouseGeneAdmin(admin.ModelAdmin):
    list_display = ('mouse_name', 'gene_name', 'zygosity',)

class GenotypeAdmin(admin.ModelAdmin):
    ordering = ('name',)

    ## Define what shows up on the individual mouse admin page
    fieldsets = (
        (None, {
            'fields': ('name',),
            'description': 'ANY CHANGE YOU MAKE HERE WILL AFFECT EVERY '
                'MOUSE WITH THIS GENOTYPE! This is almost never what you '
                'want to do. If you just want to change one mouse\'s '
                'genotype, then close this window, and choose a different '
                'genotype from the dropdown list, or click the plus button '
                'to create a new one.',
        }),
    )

class PersonAdmin(admin.ModelAdmin):
    ordering = ('name',)

class SpecialRequestAdmin(admin.ModelAdmin):
    list_display = ('cage', 'requester', 'requestee', 'date_requested', 
        'date_completed', 'message',)
    list_filter = ('requester', 'requestee')

class HistoricalMouseAdmin(admin.ModelAdmin):
    list_filter = ('cage__name', 'name',)
    search_fields = ('name', 'cage__name')
    list_display = ('history_date', 'history_user', 'name', 'cage', 'notes',
        #'genotype',
        )
    change_list_template = 'admin/colony/historicalmouse/change_list.html'


admin.site.register(HistoricalMouse, HistoricalMouseAdmin)
admin.site.register(Mouse, MouseAdmin)
admin.site.register(Gene, GeneAdmin)
admin.site.register(MouseGene, MouseGeneAdmin)
admin.site.register(Genotype, GenotypeAdmin)
admin.site.register(Litter, LitterAdmin)
admin.site.register(Cage, CageAdmin)
admin.site.register(Person, PersonAdmin)
admin.site.register(SpecialRequest, SpecialRequestAdmin)