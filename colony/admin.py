from django.contrib import admin
from .models import (Mouse, Genotype, Litter, 
    Cage, Person, Task)
# Register your models here.
from django.db.models import Count
import nested_inline.admin
from django.core import urlresolvers

class MouseInline(nested_inline.admin.NestedTabularInline):
    """Nested within Litter, so this is for adding pups"""
    model = Mouse
    extra = 1
    
    # Exclude the stuff that isn't normally specified when adding pups
    exclude = ('manual_dob', 'manual_mother', 'manual_father', 
        'sack_date', 'user', 'breeder')
    show_change_link = True    
    
    # How can we make "notes" the right-most field?

class LitterInline(nested_inline.admin.NestedStackedInline):
    """For adding a Litter to a Cage"""
    model = Litter
    extra = 0
    show_change_link = True
    inlines = [MouseInline]

class LitterAdmin(admin.ModelAdmin):
    list_display = ('breeding_cage', 'proprietor', 'info', 'target_genotype',
        'date_mated', 'age', 'father', 'mother', 'notes',)
    inlines = [MouseInline] 
    list_editable = ('notes',)
    list_filter = ('proprietor__name',)
    readonly_fields = ('target_genotype', 'info',)
    ordering = ('breeding_cage__name', )

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

class CageAdmin(nested_inline.admin.NestedModelAdmin):
    """Admin page for the Cage object.

    """
    # Columns in the list page
    list_display = ('name', 'proprietor', 'litter', 
        'target_genotype', 'link_to_mice', 
        'needs', 'need_date', 'defunct', 'notes',)
    
    # The ones that are editable
    list_editable = ('notes', )
    
    # This allows filtering by proprietor name and defunctness
    list_filter = ('proprietor__name', DefunctFilter,)
    
    # Sorting in the list page
    ordering = ('defunct', 'name',)
    
    # The readonly fields
    readonly_fields = ('infos', 'needs', 'need_date', 'target_genotype', 
        'link_to_mice',)
    
    # Litter is an inline
    inlines = [LitterInline]

    ## Define what shows up on the individual cage admin page
    # Clickable links to every mouse in the cage
    def link_to_mice(self, obj):
        """Generate HTML links for every mouse in the cage"""
        link_html_code = ''
        for child in obj.mouse_set.order_by('name').all():
            child_link = urlresolvers.reverse("admin:colony_mouse_change", 
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
            'fields': ('name', 'location', 'proprietor',),
            'description': 'Required properties',
        }),
        (None, {
            'fields': ('notes', 'defunct',),
            'description': 'Optional properties',
        }),        
        (None, {
            'fields': ('link_to_mice',),
            'description': 'Mice in this cage',
        }),                     
        (None, {
            'fields': ('target_genotype', 'needs', 'need_date',),
            'description': 'Litter husbandry information',
        }),
    )

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
    #search_fields = ['name']
    
    # This controls the columns that show up on the Admin page for Mouse
    list_display = ('name', 'user', 'dob', 'age', 'sacked', 'sex', 'cage', 
        'breeder', 'genotype', 'notes',)
    list_editable = ('notes',)
    readonly_fields = ('info', 'age', 'dob', 'mother', 'father', 'sacked', 
        'link_to_mother', 'link_to_father', 'link_to_progeny',
        'link_to_cage',)
    #~ list_display_links = ('name', 'litter', 'cage')
    list_filter = ['cage__proprietor', 'breeder', SackFilter, 
        'genotype__name', ]
    
    # How it is sorted by default
    ordering = ('name',)
    
    ## Create fields that are HTML links to other mice
    # http://stackoverflow.com/questions/28832897/link-in-django-admin-to-foreign-key-object
    def link_to_mother(self, obj):
        link = urlresolvers.reverse("admin:colony_mouse_change", 
            args=[obj.mother.id])
        return u'<a href="%s">%s</a>' % (link, obj.mother.name)
    link_to_mother.allow_tags=True    
    
    def link_to_father(self, obj):
        link = urlresolvers.reverse("admin:colony_mouse_change", 
            args=[obj.father.id])
        return u'<a href="%s">%s</a>' % (link, obj.father.name)
    link_to_father.allow_tags=True    

    def link_to_cage(self, obj):
        link = urlresolvers.reverse("admin:colony_cage_change", 
            args=[obj.cage.id])
        return u'<a href="%s">%s</a>' % (link, obj.cage.name)
    link_to_cage.allow_tags=True    

    def link_to_progeny(self, obj):
        """Generate HTML links for every child"""
        link_html_code = ''
        for child in obj.progeny:
            child_link = urlresolvers.reverse("admin:colony_mouse_change", 
                args=[child.id])
            child_info = child.info()
            if child_info is None or child_info == '':
                child_info = 'pup'
            link_html_code += u'<a href="%s">%s</a><br />' % (
                child_link, child_info)
        return link_html_code
    link_to_progeny.allow_tags=True    

    ## Define what shows up on the individual mouse admin page
    fieldsets = (
        (None, {
            'fields': ('name', 'sex', 'genotype',),
            'description': 'Required properties',
        }),
        (None, {
            'fields': ('cage', 'link_to_cage', 'sack_date', 
                'breeder', 'user', 'notes', 'litter',),
            'description': 'Optional properties',
        }),        
        (None, {
            'fields': ('link_to_mother', 'link_to_father', 'link_to_progeny'),
            'description': 'Genealogy',
        }),                
        (None, {
            'fields': ('age', 'manual_father', 'manual_mother', 'manual_dob',),
            'description': (
                'These properties are normally derived from the litter. '
                'Override mother, father, and DOB here if necessary.'),
        }),        
    )

    #~ # Was hoping to get filtering by sacked working, but doesn't seem to
    #~ def get_queryset(self, request):
        #~ qs = super(MouseAdmin, self).get_queryset(request)
        #~ return qs.annotate(is_sacked=Count('sack_date'))
    

class GenotypeAdmin(admin.ModelAdmin):
    ordering = ('name',)

class PersonAdmin(admin.ModelAdmin):
    ordering = ('name',)

class TaskAdmin(admin.ModelAdmin):
    list_display = ('assigned_to', 'created_by', 'notes', 'cage_names',)
    list_editable = ('notes',)

admin.site.register(Mouse, MouseAdmin)
admin.site.register(Genotype, GenotypeAdmin)
admin.site.register(Litter, LitterAdmin)
admin.site.register(Cage, CageAdmin)
admin.site.register(Person, PersonAdmin)
admin.site.register(Task, TaskAdmin)