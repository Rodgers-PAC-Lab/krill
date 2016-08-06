from django.contrib import admin
from .models import (Mouse, Genotype, Litter, 
    Cage, Person, Task)
# Register your models here.
from django.db.models import Count
import nested_inline.admin

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
    list_editable = ('notes', 'date_checked')
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
    # This is an example of how to put a traversal in the table
    # Can add 'get_target_genotype' to list_display
    # But I implemented it as a method on Cage instead
    #~ def get_target_genotype(self, obj):
        #~ """Helper function to traverse litter to get target genotype"""
        #~ return obj.litter.target_genotype
    #~ get_target_genotype.admin_order_field = 'target_genotype'
    #~ get_target_genotype.short_description = 'Target'
    
    list_display = ('name', 'proprietor', 'litter', 
        'target_genotype', 'infos', 
        'needs', 'need_date', 'defunct', 'notes',)
    list_editable = ('notes', )
    
    list_filter = ('proprietor__name', DefunctFilter,)
    
    ordering = ('defunct', 'name',)
    readonly_fields = ('infos', 'needs', 'need_date',)
    inlines = [LitterInline]

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
        'breeder', 'genotype', 'notes')
    list_editable = ('notes',)
    readonly_fields = ('info', 'age', 'dob', 'mother', 'father', 'sacked',)
    #~ list_display_links = ('name', 'litter', 'cage')
    list_filter = ['cage__proprietor', 'breeder', SackFilter, 
        'genotype__name', ]
    
    # How it is sorted by default
    ordering = ('name',)
    
    # This controls what you see on the individual mouse page
    # Would be better to break this up into sections
    #~ fieldsets = (
        #~ (None, {
            #~ 'fields': ('name', 'dob', 'father', 'mother', 
            #~ 'manual_dob', 'manual_father', 'manual_mother',
            #~ 'age', 'sack_date', 'sex', 'cage', 'genotype', 'litter', 'notes', 'info'),
            #~ 'description': 'Specify manual_dob, manual_father, and manual_mother only if not available in litter info',
        #~ }),
    #~ )
    #ordering = ['dob']

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