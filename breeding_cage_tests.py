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
father = colony.models.Mouse.objects.filter(name="fakedad")[0]
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
if mom has previous litters and they have a dob and previous dad is same as current dad: