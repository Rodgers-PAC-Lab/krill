import colony.models
import datetime
import pandas

# Want to find a way to get a new mating cage to use the previous litter's DOB as the mating date
# instead of just using the date of cage creation.
# Testing with one mom
cakemom = colony.models.Mouse.objects.filter(name="1096-2")[0]
cakecage=cakemom.cage
# Find all litters born to this mom
cakes_litters = colony.models.Litter.objects.filter(mother=cakemom)
current_cakelitter = cakes_litters.latest("dob")
# Find the DOB for last litter born to this mom excluding the current unborn litter
previous_dob = cakes_litters.filter(dob__isnull=False).latest("dob").dob

# Validate that the current litter is in the mom's cage, doesn't have a DOB, and
#if current_cakelitter.breeding_cage == cake:


mother = colony.models.Mouse.objects.filter(name="fakemom")[0]
father = colony.models.Mouse.objects.filter(name="fakedad2")[0]
prev_litters = colony.models.Litter.objects.filter(mother=mother)
def get_mating_date(mother,father):
    if prev_litters.exists():
        # Excludes mothers with no previous litters at all
        if prev_litters.filter(dob__isnull=False).filter(father=father).exists():
            # If the previous litter was from the same parents,
            # assume the mating date is dob of the previous litter
            previous_dob = prev_litters.filter(dob__isnull=False).filter(father=father).latest("dob").dob
            date_mated = previous_dob
        else:
            date_mated = datetime.date.today()
 #           print("catch 1")
    else:
        # If there are no previous litters, date_mated is today.
        date_mated = datetime.date.today()
    return date_mated


fakelitters = colony.models.Litter.objects.filter(mother=mother)

fakecage = colony.models.Cage.objects.filter(name='fakebreed3').get()
testfake = colony.models.Litter.objects.filter(breeding_cage=fakecage).get()


def needs_pup_check(self):
    """Returns information about when pup check is needed.

    If the litter does not have a date mated: returns None
    Otherwise: Like all need_* methods, returns dict with
        trigger, target, and warn dates; as well as a message.
    """
    if not self.date_mated or self.dob:
        return None

    reference_date = self.date_mated
    checked_date = self.date_checked
    trigger = reference_date + datetime.timedelta(days=20)
    target = reference_date + datetime.timedelta(days=25)
    warn = reference_date + datetime.timedelta(days=35)
    if target <= checked_date:
        target = checked_date + datetime.timedelta(days=3)


    return {'message': 'pup check',
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
        self.needs_wean,
    ]
    today = datetime.date.today()
    checked_date = self.date_checked
    # Iterate over needs methods
    for meth in meth_l:
        meth_res = meth()
        print(meth)
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


meth_l = [
        testfake.needs_date_mated,
        testfake.needs_pup_check,
        testfake.needs_wean,
    ]
today = datetime.date.today()
checked_date = testfake.date_checked