"""
TODO
Validation scripts that check that the genotype of each mouse meshes with
the parents
Auto-determine needed action for each litter (and breeding cage?)
Auto-id litters
Slug the mouse name from the litter name and toe num?
"""


from __future__ import unicode_literals

from django.db import models
import datetime
from django.core import urlresolvers

# Create your models here.

class Person(models.Model):
    name = models.CharField(max_length=15, unique=True)    
    
    def __str__(self):
        return self.name

class Task(models.Model):
    assigned_to = models.ForeignKey('Person', related_name='assigned_to')
    created_by = models.ForeignKey('Person', related_name='created_by')
    notes = models.CharField(max_length=150)
    cages = models.ManyToManyField('Cage', blank=True)
    
    def cage_names(self):
        cage_l=[]
        for c in self.cages.all():
            cage_l.append(c.name)
        return ', '.join(cage_l)
    
class Cage(models.Model):
    name = models.CharField(max_length=10, unique=True)    
    notes = models.CharField(max_length=100, blank=True, null=True)
    defunct = models.BooleanField(default=False)
    location = models.IntegerField(
        choices = (
            (0, '1710'),
            (1, '1702'),
            (2, 'Behavior'),
            ),
        default=0
        )
    
    # Needs to be made mandatory
    proprietor = models.ForeignKey('Person')

    def notes_first_half(self, okay_line_length=25):
        """Return the first half of the notes. For CensusView display
        
        Deprecated since we started specifying CensusView column widths.
        """
        s = str(self.notes)
        if len(s) < okay_line_length or ' ' not in s:
            return s
        
        # Find all spaces
        spi = [i for i, letter in enumerate(s) if letter == ' ']
        dist_from_center = [abs(spii - len(s) / 2) for spii in spi]

        # Find the space closest to the middle of the string
        best_space_idx, min_dist_from_center = min(enumerate(
            dist_from_center), key=lambda x:x[1])
        split_idx = spi[best_space_idx]
        
        return s[:split_idx]
    
    def notes_second_half(self, okay_line_length=25):
        s = str(self.notes)
        if len(s) < okay_line_length or ' ' not in s:
            return ''
        
        # Find all spaces
        spi = [i for i, letter in enumerate(s) if letter == ' ']
        dist_from_center = [abs(spii - len(s) / 2) for spii in spi]

        # Find the space closest to the middle of the string
        best_space_idx, min_dist_from_center = min(enumerate(
            dist_from_center), key=lambda x:x[1])
        split_idx = spi[best_space_idx]
        
        return s[split_idx:]

    def get_special_request_message(self):
        res_l = []
        for sr in self.specialrequest_set.all():
            if sr.date_completed is None:
                res_l.append("<b>%s: %s</b>" % (sr.requestee, sr.message))
            else:
                res_l.append("<strike>%s: %s</strike>" % (sr.requestee, sr.message))
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
        """If contains a non-weaned Litter, return target genotype of it"""
        if self.litter and not self.litter.date_weaned:
            return self.litter.target_genotype
    
    def change_link(self):
        """Get a link to the change page
        
        Probably doesn't belong in models.py
        """
        return urlresolvers.reverse("admin:colony_cage_change", args=[self.id])        
    
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
    def __str__(self):
        return self.name

class Mouse(models.Model):
    """Model for a Mouse.
    
    Required fields
        name: unique. Should almost always be LITTERNUM-TOENUM
        sex: M, F, or ?
        genotype: foreign key to genotype
    
    Optional fields that are often set
        cage: cage object in which this mouse is physically located
        sack_date: date of death
        breeder: boolean, used mainly for filtering in MouseList to see
            whether we have enough breeders

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
    # Required fields
    name = models.CharField(max_length=15, unique=True)
    sex = models.IntegerField(
        choices=(
            (0, 'M'),
            (1, 'F'),
            (2, '?'),
            )
        )
    genotype = models.ForeignKey(Genotype)
    
    # Optional fields that can be set by the user
    cage = models.ForeignKey(Cage, null=True, blank=True)
    sack_date = models.DateField('sac date', blank=True, null=True)
    breeder = models.BooleanField(default=False)
    user = models.ForeignKey(Person, null=True, blank=True)    
    notes = models.CharField(max_length=100, null=True, blank=True)    
    
    # These fields are normally calculated from Litter but can be overridden
    manual_dob = models.DateField('DOB override', blank=True, null=True)
    manual_father = models.ForeignKey('Mouse', 
        null=True, blank=True, related_name='mmf')
    manual_mother = models.ForeignKey('Mouse', 
        null=True, blank=True, related_name='mmm')

    # This field is almost always set at the time of creation of a new Litter
    litter = models.ForeignKey('Litter', null=True, blank=True)
    
    # To always sort mice within a cage by name, eg in census view
    class Meta:
        ordering = ['name']
    
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
        
        %NAME% (%SEX% %AGE% %GENOTYPE% %USER%)
        """
        res = "%s (%s " % (self.name, self.get_sex_display())

        # Add age if we know it
        age = self.age()
        if age is not None:
            res += 'P%d ' % age
        
        # Always add genotype
        res += str(self.genotype)
        
        # Add user if we know it
        if self.user:
            res += ' [%s]' % str(self.user)
        
        # Finish
        res += ')'
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
    
    # This is no longer necessary because the manual_dob field is used
    # to contain this information. In fact we *don't* want to autosave
    # the DOB in this way, because if the litter DOB is changed later, then
    # we want the mouse DOB to automatically update.
    #~ def save(self, *args, **kwargs):
        #~ if self.litter and not self.pk:
            #~ self.manual_dob = self.litter.dob
        #~ return super(Mouse, self).save(*args, **kwargs)

    def save(self, *args, **kwargs):
        # When creating pup in a litter nested inline, automatically place
        # in the breeding cage
        if self.litter and self.litter.breeding_cage and not self.pk:
            self.cage = self.litter.breeding_cage
        return super(Mouse, self).save(*args, **kwargs)

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
    # If we set it true, it implie null=False and unique=True
    # Probably this is good because it will auto-create a Litter for every
    # new Cage, which may save a manual step?
    breeding_cage = models.OneToOneField(Cage,
        on_delete=models.CASCADE,
        primary_key=True)    
    
    # Required field
    proprietor = models.ForeignKey(Person, default=1)

    # ForeignKey to father and mother of Litter
    father = models.ForeignKey('Mouse',
        related_name='bc_father',
        limit_choices_to={'sex': 0})
    mother = models.ForeignKey('Mouse',
        related_name='bc_mother',
        limit_choices_to={'sex': 1})

    # Optional fields relating to dates
    date_mated = models.DateField('parents mated', null=True, blank=True)
    dob = models.DateField('date of birth', null=True, blank=True)
    date_toeclipped = models.DateField('toe clip', null=True, blank=True)
    date_weaned = models.DateField('weaned', null=True, blank=True)
    date_checked = models.DateField('last checked', null=True, blank=True)
    
    # Other optional fields
    notes = models.CharField(max_length=100, null=True, blank=True)
    pcr_info = models.CharField(max_length=50, null=True, blank=True)
    
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
        return self.info
    
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

    @property
    def target_genotype(self):
        """Returns string: the father's genotype x the mother's."""
        return str(self.father.genotype) + ' x ' + str(self.mother.genotype)
    
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
        trigger = reference_date + datetime.timedelta(days=17)
        target = reference_date + datetime.timedelta(days=20)
        warn = reference_date + datetime.timedelta(days=20)
        
        return {'message': 'wean',
            'trigger': trigger, 'target': target, 'warn': warn}

    def auto_needs_message(self):
        """Generates an HTML string with all of the litter auto-needs.
        
        Iterates through all of the needs_* methods and generates
        an HTML string with all of them. Displayed in census view.        
        """
        results_s_l = []
        meth_l = [
            self.needs_date_mated,
            self.needs_pup_check,
            self.needs_toe_clip,
            #~ self.needs_genotype,
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

    def save(self, *args, **kwargs):
        if self.breeding_cage and not self.pk:
            self.proprietor = self.breeding_cage.proprietor
        return super(Litter, self).save(*args, **kwargs)

class SpecialRequest(models.Model):
    cage = models.ForeignKey(Cage)
    message = models.CharField(max_length=150)
    requester = models.ForeignKey(Person, null=True, blank=True,
        related_name='requests_from_me')
    requestee = models.ForeignKey(Person, null=True, blank=True,
        related_name='requests_for_me')
    date_requested = models.DateField('date requested', null=True, blank=True)
    date_completed = models.DateField('date completed', null=True, blank=True)