"""This defines the models for each object in the colony, such as Cage.

TODO
Validation scripts that check that the genotype of each mouse meshes with
the parents
Auto-determine needed action for each litter (and breeding cage?)
Auto-id litters
Slug the mouse name from the litter name and toe num?
"""


from __future__ import unicode_literals
from __future__ import division

import numpy as np

from builtins import str
from builtins import zip
from past.utils import old_div
from builtins import object
from django.db import models
import datetime
from django.urls import reverse
from django.urls.exceptions import NoReverseMatch
from simple_history.models import HistoricalRecords
from django.utils import timezone
from django.utils.html import escape
from django.contrib.auth.models import User
from django.utils.safestring import mark_safe
from autoslug import AutoSlugField

def strip_alpha(cage_name):
    """Keep only digits from cage name
    
    Ignores any initial alpha characters
    Then takes digits until the next alpha character is reached
    Then returns the digits as an integer, or None if no match.
    """
    res = ''
    started_taking_digits = False
    for char in cage_name:
        if not started_taking_digits:
            if char in '0123456789':
                started_taking_digits = True
                res += char
            else:
                continue
        else:
            if char in '0123456789':
                res += char
            else:
                break
    
    if len(res) == 0:
        return None
    else:
        return int(res)

def generate_cage_name(series_number):
    """Returns the next cage name for this user.
    
    series_number : series number to generate the cage number
    
    Finds all existing cage names and chooses one number higher.
    Returns: the new cage name as a string
    """
    # Find all cage numbers in this series
    all_cage_names = Cage.objects.all().values_list('name', flat=True)
    my_cage_numbers = []
    for cage_name in all_cage_names:
        try:
            cage_num = int(cage_name)
        except (TypeError, ValueError):
            continue
        if (cage_num // 1000 == series_number):
            my_cage_numbers.append(cage_num)
    
    # This was a previous algorithm that failed after 9999
    #~ my_cages = Cage.objects.filter(name__startswith=str(series_number))
    #~ cage_names = list(my_cages.values_list('name', flat=True))
    #~ cage_numbers = map(strip_alpha, cage_names)
    #~ cage_numbers = filter(lambda num: num is not None, cage_numbers)
    
    # Generate a new cage number that is 1 higher
    if len(my_cage_numbers) == 0:
        target_cage = series_number * 1000 + 1
    else:
        target_cage = max(my_cage_numbers) + 1
    #~ target_cage_name = '%04d' % target_cage
    target_cage_name = str(target_cage)
    
    # Error check
    if not target_cage_name.startswith(str(series_number)):
        raise ValueError("cannot generate new cage name, series full?")
    if Cage.objects.filter(name=target_cage_name).count() > 0:
        raise ValueError("cannot generate new unique cage name")
    
    return target_cage_name

class Person(models.Model):
    """Model of a person (experimenter)
    
    This is distinct from the "user" defined by django auth.
    
    name : the person's name
    active : boolean
        Whether to display them as an option in menus
    """
    # The Person name (name displaying on cages, etc.)
    name = models.CharField(max_length=15, unique=True,
        help_text='the name to display on their cages and mice')    
    
    # The username (login name)
    # This must manually be set and must match the User
    login_name = models.CharField(max_length=15,
        help_text=(
            'this must be manually set to be the same as their '
            'login name in order to make their personalized census view work'
        ),
        unique=True,
    )
    
    # Whether to display them
    active = models.BooleanField(default=True,
        help_text='whether to display as a possible option in menus')
    
    # Series number of their cages
    series_number = models.IntegerField(
        default=9,
        help_text='cage series number',
        null=False, blank=False,
    )
    
    # track history with simple_history
    history = HistoricalRecords()
    
    def __str__(self):
        return self.name

    # Always order by name
    class Meta(object):
        ordering = ['name']

def slug_target_genotype(litter):
    """Function to generate a target genotype slug from a cage
    
    The model itself calls this function via AutoSlugField.
    
    If the litter has already been weaned, or if its cage is defunct,
    then this returns 'NA'. That's because we typically only use this
    for filtering for active litters.
    
    To generate the slug, we first get the genotype of both parents. Then
    try to put the driver line first and the reporter second. If we
    can't identify which is which, return in alphabetical order.
    
    TODO: redo this using the new genotype detection logic
    """
    if litter.breeding_cage.defunct:
        return 'NA'
    
    g1 = str(litter.father.genotype)
    g2 = str(litter.mother.genotype)
    drivers = ['cre']
    reporters = ['flex', 'halo', 'tdtomato', 'mcherry']
    for driver in drivers:
        if driver in g1.lower():
            return g1 + ' x ' + g2
        elif driver in g2.lower():
            return g2 + ' x ' + g1
    
    for reporter in reporters:
        if reporter in g2.lower():
            return g1 + ' x ' + g2
        elif reporter in g1.lower():
            return g2 + ' x ' + g1
    
    if g1 < g2:
        return g1 + ' x ' + g2
    else:
        return g2 + ' x ' + g1

def my_slugify(s):
    """Don't apply any prettification to the slug, such as removing +"""
    return s

def have_same_single_gene(mouse1, mouse2):
    """Returns True if mouse1 and mouse2 have the same single MouseGene
    
    This is mainly useful for detecting homozygosing crosses
    """
    if mouse1.mousegene_set.count() != 1:
        return False
    if mouse2.mousegene_set.count() != 1:
        return False
    
    mg1 = mouse1.mousegene_set.first()
    mg2 = mouse2.mousegene_set.first()
    
    if mg1.gene_name.id == mg2.gene_name.id:
        return True
    else:
        return False

class Cage(models.Model):
    """Model for a Cage.
    
    Each Mouse can have a ForeignKey to the Cage in which it lives.
    
    Required fields:
        name
        defunct
        location
        proprietor
        dar_type
    
    Optional (blankable) fields:
        notes
        rack_spot
        dar_id
    
    Provides methods:
        relevant_genesets
        printable_relevant_genesets
        type_of_cage
        get_special_request_message
        n_mice
        names
        infos
        age
        auto_needs_message
        target_genotype
        change_link
        contains_mother_of_this_litter
    """
    ## Required fields
    # Name of the cage
    name = models.CharField(
        max_length=50, unique=True, help_text='a unique name for this cage')    
    
    # Whether it is "defunct", meaning no longer physically present
    defunct = models.BooleanField(
        default=False, 
        help_text='set True when the cage no longer physically exists')
    
    # Where the cage physically exists
    location = models.IntegerField(
        choices = (
            (0, 'L44'),
        ), default=0,
        help_text='where the cage is physically located',
    )
    
    # Who is responsible for the cage
    proprietor = models.ForeignKey('Person',
        limit_choices_to={'active': True},
        on_delete=models.PROTECT,
        help_text='the person responsible for the cage',
    )
    
    
    ## Optional fields
    # Location on the rack
    rack_spot = models.CharField(max_length=10, blank=True,
        help_text='location within the rack')
    
    # Custom notes
    notes = models.CharField(max_length=100, blank=True, 
        help_text='any custom notes about this cage')

    # DAR number
    dar_id = models.CharField(
        max_length=100, blank=True,
        verbose_name='DAR ID number',
        help_text='the long number under the barcode')
    
    # DAR requisition number
    dar_req_num = models.CharField(
        max_length=100, blank=True, 
        verbose_name='DAR requisition number',
        help_text='(for purchased only) the DAR requisition number')
    
    # DAR cage type
    dar_type = models.IntegerField(
        choices = (
            (0, 'unknown (must specify)'),
            (1, 'separation'),
            (2, 'weaning'),
            (3, 'ordered/imported'),
            ),
        default=0,
        verbose_name='DAR type',
        help_text='where the cage came from, and what kind of card it has',
        )
    
    # Cage color
    color = models.CharField(
        max_length=20, blank=True,
        help_text='color of the cage card')
    
    # Cage sticker
    sticker = models.CharField(
        max_length=100, blank=True,
        help_text='sticker that is on the cage card',
        )
    
    ## Track history with simple_history
    history = HistoricalRecords()
    
    
    ## Below are methods
    # Always order by name
    class Meta(object):
        ordering = ['name']
    
    @property
    def relevant_genesets(self):
        """The relevant genes for the colony view
        
        If it's a breeding cage (litter is defined and unweaned), then 
        the result is a list with one item: set of all mousegenes from 
        either parent.
        
        If it's not a breeding cage (litter weaned, or undefined), then
        the result is a list of distinct mousegene sets from each pup.
        
        The interpretation depends on type_of_cage
        Examples:
            * A cage of Cux2-CreER breeders
                type_of_cage = 'pure stock'
                relevant_genes = [('Cux2-CreER',)]
            * A mating cage of Cux2 and Halo
                type_of_cage = 'cross'
                relevant_genes = [('Cux2-CreER', 'flex-halo',)]
            * A cage of Cux2-Halo progeny
                type_of_cage = 'progeny'
                relevant_genes = [('Cux2-CreER', 'flex-halo',)]
        
        The most reasonable sort is probably by relevant_genes, and then
        by type_of_cage.
        """
        cage_type = self.type_of_cage
        
        if cage_type == 'empty':
            res = []
        elif cage_type in ['outcross', 'incross', 'cross', 
            'impure outcross', 'impure incross', 'impure cross', ]:
            ## Combine mousegenes from all parents
            # The result will be a list with one element
            # That element will be a tuple of all the distinct gene names
            # in the parents.
            father = self.litter.father
            mother = self.litter.mother
            
            # Extract the gene names and types from each parent
            # This syntax was chosen to be SQL efficient with prefetching
            gene_name_res = []
            gene_type_res = []
            for parent in [father, mother]:
                for mg in parent.mousegene_set.all():
                    if mg.gene_name.name not in gene_name_res:
                        gene_name_res.append(mg.gene_name.name)
                        gene_type_res.append(mg.gene_name.gene_type)
            
            # Sort the gene names by the gene types
            sorted_gene_names = [gene_name for gene_type, gene_name in 
                sorted(zip(gene_type_res, gene_name_res))]
            
            res = [tuple(sorted_gene_names)]
        elif cage_type in ['pure stock', 'progeny',]:
            ## List of mousegene sets from each mouse
            # The result will be a list of distinct tuples of gene names
            # in each mouse in the cage.
            res = []
            for mouse in self.mouse_set.all():
                # Extract the gene names and types from this pup                
                gene_name_res = []
                gene_type_res = []  
        
                # This syntax was chosen to be SQL efficient with prefetching
                for mg in mouse.mousegene_set.all():
                    gene_name_res.append(mg.gene_name.name)
                    gene_type_res.append(mg.gene_name.gene_type)
                
                # Sort the gene names by the gene types
                sorted_gene_names = tuple([
                    gene_name for gene_type, gene_name in 
                    sorted(zip(gene_type_res, gene_name_res))])
                
                # Append if distinct
                if sorted_gene_names not in res:
                    res.append(sorted_gene_names)
        else:
            # This is an error
            res = []
        
        return res
    
    @property
    def printable_relevant_genesets(self):
        """Convert relevant genesets to a string"""
        if len(self.relevant_genesets) == 0:
            # This shouldn't really happen, unless it's empty?
            return 'empty'
        else:
            res_l = []
            for geneset in self.relevant_genesets:
                if len(geneset) == 0:
                    joined_geneset = 'WT'
                else:
                    joined_geneset = ' x '.join(geneset)
                res_l.append(joined_geneset)
            return '; '.join(res_l)
    
    @property
    def type_of_cage(self):
        """Return the type of the cage as a string
    
        It is a breeding cage if it has a litter attribute AND (the mother
        is still in the cage, or the cage is empty). This includes the 
        case where the pups were weaned into another cage and the 
        mother left behind. It also includes the case where all the mice
        are gone.
        
        It is not a breeding cage if it does not have a litter attribute,
        or (the cage has some mice but not the mother). This includes the 
        case where the pups were weaned by moving the mother somewhere else.
        
        Breeding cages (litter is defined and unweaned)
        * 'outcross' : one parent WT
        * 'incross' : both parents have_same_single_gene
        * 'cross' : anything else
        This result is prepended with 'impure' if either of the parents
        are not pure_breeder. (wild_type implies pure_breeder.)
        
        Non-breeding cages (litter is undefined or weaned)
        * 'empty' : no mice
        * 'pure stock' : all mice pure_breeder
        * 'progeny' : anything else
        """
        res = None
        qs = self.mouse_set
        
        mother_in_cage = self.contains_mother_of_this_litter
        is_empty = qs.count() == 0
        has_litter_obj = hasattr(self, 'litter')
        
        # Depends on whether there's a litter or not
        if has_litter_obj and (mother_in_cage or is_empty):
            # It is a breeding cage
            mother = self.litter.mother
            father = self.litter.father
            
            # wild_type implies pure_breeder
            mother_pure = mother.pure_wild_type or mother.pure_breeder
            father_pure = father.pure_wild_type or father.pure_breeder
            
            # determine the type of cross
            if mother.pure_wild_type or father.pure_wild_type:
                if mother_pure and father_pure:
                    res = 'outcross'
                else:
                    res = 'impure outcross'
            elif have_same_single_gene(mother, father):
                if mother_pure and father_pure:
                    res = 'incross'
                else:
                    res = 'impure incross'
            else:
                if mother_pure and father_pure:
                    res = 'cross'
                else:
                    res = 'impure cross'        
        else:
            # no breeding
            if qs.count() == 0:
                res = 'empty'
            elif False not in [mouse.pure_breeder for mouse in qs.all()]:
                # The syntax of this conditional was chosen to be efficient
                res = 'pure stock'                   
            else:
                res = 'progeny'
        
        return res

    def get_special_request_message(self):
        res_l = []
        for sr in self.specialrequest_set.all():
            if sr.date_completed is None:
                res_l.append("<b>@%s: %s</b>" % (
                    sr.requestee, escape(sr.message)))
            else:
                res_l.append("<strike>@%s: %s</strike>" % (
                    sr.requestee, escape(sr.message)))
        return '<br>'.join(res_l)

    def n_mice(self):
        return len(self.mouse_set.all())
    
    def names(self):
        """Return list of all mice in this cage"""
        name_l = []
        for m in self.mouse_set.all():
            name_l.append(m.name)
        return ', '.join(name_l)
    
    def infos(self):
        """Return list of all mice in this cage with additional info on each"""
        # Get info from each contained mouse and prepend "pup" to pups
        info_l = []
        for mouse in self.mouse_set.order_by('name').all():
            m_info = mouse.info()
            if mouse.still_in_breeding_cage:
                m_info = 'pup ' + m_info
            info_l.append(m_info)
        
        return '<pre>' + '<br>'.join(info_l) + '</pre>'
    
    # I think this is to allow a user-readable column name in admin
    infos.allow_tags = True
    infos.short_description = "Mouse Info"

    def age(self):
        age = None
        for mouse in self.mouse_set.all():
            if age is None:
                age = mouse.age()
            elif age != mouse.age():
                return None
        return age
    
    def __str__(self):
        return self.name
    
    @mark_safe
    def auto_needs_message(self):
        srm = self.get_special_request_message()
        try:
            lanm = self.litter.auto_needs_message()
        except Litter.DoesNotExist:
            lanm = ''
        
        if srm != '' and lanm != '':
            return srm + '<br />' + lanm
        else:
            return srm + lanm
    auto_needs_message.allow_tags = True
    
    def target_genotype(self):
        if self.litter:
            return self.litter.target_genotype
        else:
            return 'NA'
    target_genotype.admin_order_field = 'litter__target_genotype'
    
    def change_link(self):
        """Get a link to the change page
        
        Probably doesn't belong in models.py
        """
        return reverse("admin:colony_cage_change", args=[self.id])        
    
    @property
    def contains_mother_of_this_litter(self):
        """Returns True if the mother of this cage's litter is still present.
        
        This is True while she is raising the litter but becomes False
        after the pups are weaned (which technically means the mother was
        moved to a new cage).
        
        This is used to test whether we should display info about the
        "litter" in various views. Typically we don't really care about
        it as a "litter" after weaning, at least for the purposes of
        determining what the litter needs.
        
        Actually, a simpler way would just be to test if the litter
        has a wean date.
        """
        # Return False if litter doesn't exist
        try:
            self.litter
        except Litter.DoesNotExist:
            return False
        
        if self.litter:
            if self.litter.mother:
                if self.litter.mother.cage:
                    if self.litter.mother.cage == self:
                        # The mother exists and is still here
                        return True
                    else:
                        # The mother exists but is in another cage
                        return False
                else:
                    # No cage set for the mother
                    return False
            else:
                # no mother set, probably not possible
                return False
        else:
            # litter is None, this is probably impossible
            return False

class Genotype(models.Model):
    name = models.CharField(max_length=50, unique=True)
    
    # track history with simple_history
    history = HistoricalRecords()
    
    def __str__(self):
        return self.name

class Mouse(models.Model):
    """Model for a Mouse.
    
    Required fields
        name: unique. Should almost always be LITTERNUM-TOENUM
        sex: M, F, or ?
        pure_breeder
        pure_wild_type
    
    Optional fields that are often set
        cage: cage object in which this mouse is physically located
        sack_date: date of death
        user
        notes
        tail_tattoo
        tail_sharpie

    When mice are born and added to the tabular inline for the breeding
    cage, a Litter object is created and set to be the "litter" attribute
    on this mouse.

    "Override" fields. Typically these data are calculated by traversing
    to the mouse's Litter. Some mice were grandfathered into the db or
    were purchased and so no Litter object is available.
        manual_dob : date of birth
        manual_father
        manual_mother
    """
    ## Required fields
    name = models.CharField(max_length=25, unique=True, 
        help_text='a unique name for this mouse')
    sex = models.IntegerField(
        choices=(
            (0, 'M'),
            (1, 'F'),
            (2, '?'),
            ),
        help_text='sex of the mouse, if known',
        )
    
    # Whether this mouse is a pure breeder
    # This means that any offspring it has with WT mice will also be
    # pure breeders. We will mainly use this to identify maintenance
    # cages vs experimental cages. I can't think of a reason why
    # a pure breeder would have more than one MouseGene, but maybe it's
    # possible.
    pure_breeder = models.BooleanField(default=False,
        help_text=(
            'set True if purchased from JAX etc, rather than made by crossing'
            )
        )
    
    # Whether this mouse is a wild type. It should not have any MouseGene
    # in this case. May need to have another field for "strain".
    # This should be renamed "pure_wild_type" to clarify that it
    # implies "pure_breeder" even if "pure_breeder" is not set.
    pure_wild_type = models.BooleanField(default=False,
        help_text=(
            'set True if this is a pure wild type, '
            'as opposed to a transgenic of some kind'
            )
        )


    ## Optional fields that can be set by the user
    # ForeignKey to the cage this mouse is in
    cage = models.ForeignKey(
        Cage, null=True, blank=True,
        on_delete=models.PROTECT,
        help_text='the cage this mouse lives in',
        )
    
    # Date it was sacked
    sack_date = models.DateField('sac date', blank=True, null=True,
        help_text='(if applicable) the date this mouse was sacked')
    
    # User of the mouse
    user = models.ForeignKey(Person, null=True, blank=True,
        limit_choices_to={'active': True},
        on_delete=models.PROTECT,
        help_text='(optional) the person who uses or has claimed this mouse',
        )
    
    # Tail tattoo marking
    tail_tattoo = models.CharField(max_length=10, blank=True,
        help_text='(optional) 3-character tail tattoo',
        )
    
    # Tail sharpie marks
    tail_sharpie = models.CharField(max_length=20, blank=True,
        help_text='(optional) sharpie markings on tail',
        )
    
    # Notes field
    notes = models.CharField(max_length=200, blank=True,
        help_text='(optional) custom notes about this mouse')    
    
    # These fields are normally calculated from Litter but can be overridden
    manual_dob = models.DateField('DOB override', blank=True, null=True)
    manual_father = models.ForeignKey('Mouse', 
        null=True, blank=True, related_name='mmf',
        on_delete=models.PROTECT,
        )
    manual_mother = models.ForeignKey('Mouse', 
        null=True, blank=True, related_name='mmm',
        on_delete=models.PROTECT,
        )

    # This field is almost always set at the time of creation of a new Litter
    litter = models.ForeignKey(
        'Litter', null=True, blank=True,
        on_delete=models.PROTECT,
        )

    # track history with simple_history
    history = HistoricalRecords()
    
    # To always sort mice within a cage by name, eg in census view
    class Meta(object):
        ordering = ['name']
    
    @property
    def strain_description(self):
        """Return a string describing the strain from linked MouseStrain
        
        
        """
        # Get all MouseStrain
        mouse_strain_set = self.mousestrain_set.all()
        
        # This flag is set for weight problems
        weight_is_wrong = False
        
        # If none, then return strain unknown
        if len(mouse_strain_set) == 0:
            return 'unknown_strain'
        
        elif len(mouse_strain_set) == 1:
            # Consists of only one strain
            only_mouse_strain = mouse_strain_set.first()
            
            # The weight should be exactly 1
            if only_mouse_strain.weight != 1:
                weight_is_wrong = True
            
            # Return the name of the only strain
            if weight_is_wrong:
                return '{} (bad weight)'.format(only_mouse_strain.strain_key.name)
            else:
                return only_mouse_strain.strain_key.name
        
        else:
            # Multiple strains
            strain_names = []
            
            # Iterate over strains, in alphabetical order
            for mouse_strain in mouse_strain_set.order_by('strain_key__name').all():
                # Save name
                strain_names.append(mouse_strain.strain_key.name)
                
                # Check weight is 1
                if mouse_strain.weight != 1:
                    weight_is_wrong = True
            
            # Form the string
            strain_string = ':'.join(strain_names)
            if weight_is_wrong:
                strain_string += ' (bad weight)'
            
            return strain_string
    
    @property
    def genotype(self):
        """Return a genotype string by concatenating linked MouseGene objects
        
        If wild_type:
            returns 'pure WT'
        Elif the mouse has no mousegenes, or only -/- mousegenes:
            returns 'negative'
        Otherwise:
            returns a string of the format 
                "GENE1(ZYGOSITY1); GENE2(ZYGOSITY2)..."
            Genes with zygosity -/- are not included in this string.
        """
        # If it's wild type, it shouldn't have any genes
        if not self.mousegene_set.exists() and self.pure_wild_type:
            return 'pure WT'
        
        # Get all MouseGenes other than -/-
        res_l = []
        for mg in self.mousegene_set.all():
            if mg.zygosity == MouseGene.zygosity_nn:
                continue
            res_l.append('%s(%s)' % (mg.gene_name, mg.zygosity))
        
        if len(res_l) == 0:
            # It has no mousegenes, or only -/- mouse genes
            # Render as 'negative'. Avoid confusion with 'WT'
            # Also don't include the 'pure' because 'pure negative'
            # is confusing.            
            return 'negative'
        else:
            # Join remaining mousegenes
            return '; '.join(res_l)
    
    def get_cage_history_list(self, only_cage_changes=True):
        """Return list of cage info at every historical timepoint.
        
        The results are sorted from oldest to most recent.
        
        only_cage_changes : if True, then only return history items that
            have a different cage name than the immediately previous item
        
        Returns: list of dicts
            Each dict has keys 'cage__name', 'history_date', 'history_user'
        """
        # List of cages at all historical timepoints
        h_list = self.history.order_by('history_date').all().values(
            'cage__name', 'history_user_id', 'history_date')
        
        # Filter by only those that changed
        if only_cage_changes:
            current_cage = None
            res = []
            for hll in h_list:
                if current_cage is None or hll['cage__name'] != current_cage:
                    res.append(hll)
                    current_cage = hll['cage__name']
            return res
        
        else:
            return h_list
    
    def cage_history_string(self, only_cage_changes=True):
        """Returns a formatted string of the cage history for this mouse"""
        hl = self.get_cage_history_list(only_cage_changes)
        res_l = []
        
        for hll in hl:
            try:
                username = User.objects.get(id=hll['history_user_id']).username
            except User.DoesNotExist:
                username = 'Unknown'
            
            res_l.append('%s Cage: %s  User: %s' % (
                timezone.localtime(hll['history_date']).strftime(
                    '%Y-%m-%d %H:%M:%S'),
                hll['cage__name'],
                username,
            ))
        
        return "<br />\n".join(res_l)
    cage_history_string.allow_tags = True
    cage_history_string.short_description = 'From oldest to newest'

    @property
    def user_or_proprietor(self):
        """Returns the person in charge of this mouse.
        
        This is determined in the following precedence order
            * self.user if it is set
            * self.cage.proprietor if self.cage is set
            * self.litter.breeding_cage.proprietor if self.litter is set
            * Otherwise None

        Probably it would make more sense to use an AutoSlugField here, that
        would update to cage's proprietor after every cage change. Also
        it would be much faster to query the database.
        """
        if self.user:
            return self.user
        
        if self.cage:
            return self.cage.proprietor
        
        if self.litter:
            return self.litter.breeding_cage.proprietor
        
        return None
    
    @property
    def sacked(self):
        return self.sack_date is not None
    
    @property
    def dob(self):
        """Property that returns the DOB of the litter, or manual override.
        
        """
        if self.manual_dob is not None:
            return self.manual_dob
        elif self.litter is not None:
            return self.litter.dob
        else:
            return None
    
    @property
    def mother(self):
        """Property that returns the mother of the litter, or manual override.
        
        """
        if self.manual_mother is not None:
            return self.manual_mother
        elif self.litter is not None:
            return self.litter.mother
        else:
            return None    

    @property
    def father(self):
        """Property that returns the father of the litter, or manual override.
        
        """
        if self.manual_father is not None:
            return self.manual_father
        elif self.litter is not None:
            return self.litter.father
        else:
            return None    
        
    def info(self):
        """Returns a verbose set of information about the mouse.
        
        %NAME% (%SEX% %AGE% %STRAIN% %GENOTYPE% %USER%)
        """
        res = "%s (%s " % (self.name, self.get_sex_display())

        # Add age if we know it
        age = self.age()
        if age is not None:
            res += 'P%d ' % age
        
        # Always add straing
        res += str(self.strain_description) + ' '
        
        # Always add genotype
        res += str(self.genotype)
        
        # Add user if we know it
        if self.user:
            res += ' [%s]' % str(self.user)
        
        # Finish
        res += ')'
        return res
    
    def identify_by(self):
        """Return information about tattoo or tail markings, if any"""
        res = ''
        if len(self.tail_tattoo) > 0:
            res += 'tat_{}'.format(self.tail_tattoo)
        
        if len(self.tail_sharpie) > 0:
            res += 'mark_{}'.format(self.tail_sharpie)
        
        return res

    @property
    def progeny(self):
        """Queries database to return all children of this mouse"""
        # Check for mice that have self as a mother or as a father
        # We don't want to want to assume based on self.sex because that
        # may be '?' or set incorrectly
        res1 = Mouse.objects.filter(litter__father=self)
        res2 = Mouse.objects.filter(litter__mother=self)

        if len(res1) > 0 and len(res2) > 0:
            raise ValueError("mouse is both a father and a mother")
        elif len(res1) == 0:
            return res2
        else:
            return res1
    
    def age(self):
        if self.dob is None:
            return None
        today = datetime.date.today()
        return (today - self.dob).days
    
    @property
    def still_in_breeding_cage(self):
        """Returns true if still in the cage it was bred in
        
        This is used to prepend "pup" to the infos.
        """
        if self.litter:
            return self.cage == self.litter.breeding_cage
        else:
            return False
    
    @property 
    def is_breedable_female(self):
        """Returns True if this mouse is female and age is >40 or unknown"""
        my_age = self.age()
        return self.get_sex_display() == 'F' and (my_age is None or my_age > 40)

    @property 
    def is_breedable_male(self):
        """Returns True if this mouse is male and age is >40 or unknown"""
        my_age = self.age()
        return self.get_sex_display() == 'M' and (my_age is None or my_age > 40)

    @property
    def can_be_breeding_mother(self):
        """Returns True if this mouse could be a breeding mother in this cage.
        
        Specifically, returns True if the mouse is_breedable_female and there
        is another mouse in the same cage that is_breedable_male.
        
        This is useful for highlighting mice that are (probably) breeding in
        the CensusView. It eventually could be used to auto-generate the
        "date parents mated" field on litters.
        
        Note that this is distinct from the "breeder" property, which is set
        manually by the user rather than inferred from the "facts on
        the ground".
        """
        if self.is_breedable_female:
            for mouse in self.cage.mouse_set.all():
                if mouse.is_breedable_male:
                    return True
        return False

    @property
    def can_be_breeding_father(self):
        """Returns True if this mouse could be a breeding father in this cage.
        
        See doc for can_be_breeding_mother
        """
        if self.is_breedable_male:
            for mouse in self.cage.mouse_set.all():
                if mouse.is_breedable_female:
                    return True
        return False
    
    def __str__(self):
        return str(self.name)

class Strain(models.Model):
    """A particular strain, such as CBA.
    
    There is just one instance of this per strain. The purpose of making
    this a class is so that people can create new Strain from the admin
    interface, instead of changing the model code.
    """
    # Name of the strain, e.g. CBA
    name = models.CharField(max_length=50, unique=True, 
        help_text='name of the strain (example: CBA/J)')
    
    # Stock number
    jax_stock_number = models.CharField(max_length=25, blank=True,
        help_text='(if applicable) stock number at JAX')

    # This makes the name appear properly in the admin StrainInline
    def __str__(self):
        return self.name

class MouseStrain(models.Model):
    """A particular mouse and a particular strain.
    
    Each mouse may have multiple MouseStrain. The "weight" determines
    how strong that strain is. For instance, if Mouse 1 has MouseStrain
    "CBA" with weight 1, and Mouse 2 has MouseStrain "C57" with weight 1,
    their progeny will have both strains with weight 1. 
    
    More complicated breeding schemes are not yet supported, but could
    be calculated using the GCD and LCM of the weights.
    """
    # The strain
    strain_key = models.ForeignKey(Strain, on_delete=models.PROTECT)
    
    # The mouse
    # When the Mouse is deleted, delete the associated MouseStrain
    mouse_key = models.ForeignKey(Mouse, on_delete=models.CASCADE)
    
    # The weight
    weight = models.IntegerField(
        default=1,
        help_text='the relative weight of this strain in this mouse',
        null=False, blank=False,
        )
    
class Gene(models.Model):
    """A particular gene, such as Emx-Cre.
    
    No reference to particular mouse or zygosity here.
    
    The type can be reporter or driver, which mainly just determines
    some things about the way they are sorted.
    """
    name = models.CharField(max_length=50, unique=True)
    
    gene_type_reporter = 'reporter'
    gene_type_driver = 'driver'
    gene_type_choices = (gene_type_reporter, gene_type_driver)
    gene_type_choices_dbl = tuple([(c, c) for c in gene_type_choices])
    gene_type = models.CharField(max_length=20, choices=gene_type_choices_dbl,
        blank=True)
    
    def __str__(self):
        return self.name
    
    class Meta(object):
        ordering = ['gene_type', 'name',]

class MouseGene(models.Model):
    """Particular gene for a particular mouse
    
    There is a separate instance for every Mouse and every one of the
    genes that it has or may have. So for instance, Mouse M1 can have
    Gene G1 (homo, tested on 10-10) and Gene G2 (het, not tested but
    known). There is just one "Gene" object for each unique Gene (e.g.,
    Emx-Cre).
    
    TODO: Many2Many key from MouseGene to GenotypingSession.
    """
    gene_name = models.ForeignKey(Gene,
        on_delete=models.PROTECT)
    # When the mouse is deleted, delete the associated mouse gene
    mouse_name = models.ForeignKey(Mouse,
        on_delete=models.CASCADE) 
    
    # Zygosity
    zygosity_yy = '+/+'
    zygosity_yn = '+/-'
    zygosity_ym = '+/?'
    zygosity_mn = '?/-'
    zygosity_mm = '?/?'
    zygosity_nn = '-/-' # not sure this one should be allowed
    zygosity_choices = (zygosity_yy, zygosity_yn, zygosity_ym,
        zygosity_mn, zygosity_mm, zygosity_nn)
    zygosity_choices_dbl = tuple([(c, c) for c in zygosity_choices])
    zygosity = models.CharField(max_length=10, choices=zygosity_choices_dbl)
    
    class Meta(object):
        ordering = ('gene_name__gene_type', 'gene_name__name',)

class Litter(models.Model):
    """Model for Litter.
    
    A Litter is a set of Mice that were born in a Cage. Each Cage should
    only ever have one Litter.
    
    Required fields:
        proprietor (Is this really necessary since we have Cage proprietor?)
        breeding_cage : OneToOne
        father
        mother
    
    Optional fields:
        date_mated
        dob
        date_toeclipped
        date_weaned
        date_checked
        notes
        pcr_info
    """
    # A one-to-one key to Cage, because each Cage can have no more than
    # one litter
    # Not sure whether to set primary_key=True here
    # If we set it true, it implies null=False and unique=True
    # Probably this is good because it will auto-create a Litter for every
    # new Cage, which may save a manual step?
    breeding_cage = models.OneToOneField(Cage,
        on_delete=models.CASCADE,
        primary_key=True)    
    
    # Required field
    proprietor = models.ForeignKey(
        Person, null=True, blank=True,
        on_delete=models.PROTECT)

    # ForeignKey to father and mother of Litter
    father = models.ForeignKey('Mouse',
        related_name='bc_father',
        limit_choices_to={'sex': 0},
        on_delete=models.PROTECT)
    mother = models.ForeignKey('Mouse',
        related_name='bc_mother',
        limit_choices_to={'sex': 1},
        on_delete=models.PROTECT)

    # The target genotype is slugged from the genotype of the mother
    # and father
    target_genotype = AutoSlugField(populate_from=slug_target_genotype,
        always_update=True,
        slugify=my_slugify,
    )

    # Optional fields relating to dates
    date_mated = models.DateField('parents mated', null=True, blank=True)
    dob = models.DateField('date of birth', null=True, blank=True)
    date_toeclipped = models.DateField('toe clip', null=True, blank=True)
    date_weaned = models.DateField('weaned', null=True, blank=True)
    date_checked = models.DateField('last checked', null=True, blank=True)
    date_genotyped = models.DateField('genotyped', null=True, blank=True)
    
    # Other optional fields
    notes = models.CharField(max_length=100, blank=True)
    pcr_info = models.CharField(max_length=50, blank=True)

    # track history with simple_history
    history = HistoricalRecords()
    
    def days_since_mating(self):
        if self.date_mated is None:
            return None
        today = datetime.date.today()
        return (today - self.date_mated).days
    
    def age(self):
        if self.dob is None:
            return None
        today = datetime.date.today()
        return (today - self.dob).days

    def __str__(self):
        return str(self.breeding_cage)
    
    @property
    def current_change_link(self):
        """Returns a string about the status of the litter for the census
        
        Will be:
            'weaned'
            '%s; add pups'
            '%s; edit'
        where %s is self.info()
        
        This should be renamed as it is not a link
        """
        if self.date_weaned is not None:
            return 'weaned'
        elif self.dob is None:
            return self.info
        elif self.mouse_set.count() == 0:
            # Needs pups added
            return '%s; add pups' % self.info
        else:
            return '%s; edit' % self.info

    @property
    def management_link(self):
        """Get a link to the litter management page"""
        try:
            return reverse("colony:add_genotyping_info", 
                args=[self.pk])   
        except NoReverseMatch:
            # After an update, this function is sometimes called with
            # None as self.pk, not sure why, so catch it here
            return None
    
    @property
    def info(self):
        """Returns a string like 10@P19"""
        bc_name = self.breeding_cage.name
        try:
            n_pups = len(self.mouse_set.all())
        except AttributeError:
            n_pups = 0
        pup_age = self.age()
        pup_embryonic_age = self.days_since_mating()
        if pup_age is None:
            if pup_embryonic_age is None:
                return '%d pups' % (n_pups)
            else:
                return 'E%s' % (pup_embryonic_age)
        else:
            return '%d@P%s' % (n_pups, pup_age)
    
    def needs_date_mated(self):
        """Returns message if litter has no date_mated.
        
        If the litter does not have a date mated: returns None
        Otherwise: Like all need_* methods, returns dict with 
            trigger, target, and warn dates; as well as a message.
        """
        if self.date_mated or self.dob:
            return None
        
        reference_date = datetime.date.today()

        return {'message': 'specify date mated',
            'trigger': reference_date, 'target': reference_date, 
            'warn': reference_date + datetime.timedelta(days=1)}
    
    def needs_pup_check(self):
        """Returns information about when pup check is needed.
        
        If the litter does not have a date mated: returns None
        Otherwise: Like all need_* methods, returns dict with 
            trigger, target, and warn dates; as well as a message.
        """
        if not self.date_mated or self.dob:
            return None
        
        reference_date = self.date_mated
        trigger = reference_date + datetime.timedelta(days=20)
        target = reference_date + datetime.timedelta(days=25)
        warn = reference_date + datetime.timedelta(days=35)
        
        return {'message': 'pup check',
            'trigger': trigger, 'target': target, 'warn': warn}

    def needs_toe_clip(self):
        """Returns information about when toe clip is needed.
        
        If the litter does not have a date of birth: returns None
        Otherwise: Like all need_* methods, returns dict with 
            trigger, target, and warn dates; as well as a message.
        """        
        if not self.dob or self.date_toeclipped:
            return None
        
        reference_date = self.dob
        trigger = reference_date + datetime.timedelta(days=0)
        target = reference_date + datetime.timedelta(days=7)
        warn = reference_date + datetime.timedelta(days=14)
        
        return {'message': 'toe clip',
            'trigger': trigger, 'target': target, 'warn': warn}

    def needs_genotype(self):
        """Returns information about when genotyping is needed.
        
        If the litter does not have a date of birth: returns None
        Otherwise: Like all need_* methods, returns dict with 
            trigger, target, and warn dates; as well as a message.
        """         
        if not self.dob or self.date_toeclipped:
            return None
        
        reference_date = self.dob
        trigger = reference_date + datetime.timedelta(days=0)
        target = reference_date + datetime.timedelta(days=17)
        warn = reference_date + datetime.timedelta(days=20)
        
        return {'message': 'genotype',
            'trigger': trigger, 'target': target, 'warn': warn}

    def needs_wean(self):
        """Returns information about when weaning is needed.
        
        If the litter does not have a date of birth: returns None
        Otherwise: Like all need_* methods, returns dict with 
            trigger, target, and warn dates; as well as a message.
        """         
        if not self.dob or self.date_weaned:
            return None
        
        reference_date = self.dob
        trigger = reference_date + datetime.timedelta(days=19)
        target = reference_date + datetime.timedelta(days=21)
        warn = reference_date + datetime.timedelta(days=22)
        
        return {'message': 'wean',
            'trigger': trigger, 'target': target, 'warn': warn}

    @mark_safe
    def auto_needs_message(self):
        """Generates an HTML string with all of the litter auto-needs.
        
        Iterates through all of the needs_* methods and generates
        an HTML string with all of them. Displayed in census view.        
        """
        results_s_l = []
        meth_l = [
            self.needs_date_mated,
            self.needs_pup_check,
            self.needs_wean,
        ]
        today = datetime.date.today()
        
        # Iterate over needs methods
        for meth in meth_l:
            meth_res = meth()
            
            # Continue if no result or not triggered
            if meth_res is None:
                continue
            if meth_res['trigger'] > today:
                continue
            
            # Form the message
            target_date_s = meth_res['target'].strftime('%m/%d')
            full_message_s = '%s on %s' % (meth_res['message'], target_date_s)
            
            # Append with warn tags
            if meth_res['warn'] <= today:
                results_s_l.append('<b>' + full_message_s + '</b>')
            else:
                results_s_l.append(full_message_s)
        
        result_s = '<br />'.join(results_s_l)
        return result_s
    auto_needs_message.allow_tags = True

class SpecialRequest(models.Model):
    """A request made by someone to someone about a certain cage."""
    cage = models.ForeignKey(Cage,
        on_delete=models.PROTECT)
    message = models.CharField(max_length=150)
    requester = models.ForeignKey(Person, null=True, blank=True,
        limit_choices_to={'active': True},
        related_name='requests_from_me',
        on_delete=models.PROTECT)
    requestee = models.ForeignKey(Person, null=True, blank=True,
        limit_choices_to={'active': True},
        related_name='requests_for_me',
        on_delete=models.PROTECT)
    date_requested = models.DateField('date requested', null=True, blank=True)
    date_completed = models.DateField('date completed', null=True, blank=True)
    
    # track history with simple_history
    history = HistoricalRecords()