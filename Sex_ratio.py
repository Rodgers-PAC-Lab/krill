import colony.models
import numpy as np
# Pseudocode to look at mouse sex in the db for bias over time...
# Want to separate by breeding cross and/or by breeding pair
# Colony_pups = mice born from our pairs, not ordered from outside
# Optional date critera and/or particular breeding pair criteria
# Pup_genesets = unique genesets in colony_pups
# For each geneset in pup_genesets:
#   M = count mouses in colony_pups where mouse_geneset=geneset and sex=M
#   F = Same but for F
# M_percentage = M/colony_pups * 100 (repeat for F)



all_litters = colony.models.Litter.objects.filter()
L_1050 = all_litters[0] #no get(), gives object not queryset huh
# QSet with all mice in litter but also like, not in a useful form?
# It's a QS of... tuples????
L_1050_mice = L_1050.mouse_set.values_list()
# Gets numerical mouse ID of first mouse in the litter.
# Use this syntax to iterate over litter and grab a QS of all mice objects if needed.
L_1050_mouseid = L_1050.mouse_set.values_list()[0][0]

all_litters = colony.models.Litter.objects.filter()
all_genotypes = all_litters.values('target_genotype').distinct()
# all_genotypes gives a queryset, but again it's a QS of dicts
# THIS gets a string of the genotype finally
gtype1 = all_genotypes[0]['target_genotype']
FAD_litters = colony.models.Litter.objects.filter(target_genotype = gtype1)
FAD_moms = FAD_litters.values('mother').distinct()
duckies_mom = colony.models.Mouse.objects.filter(id=FAD_moms[6]['mother']).get()
duckies_litters = duckies_mom.progeny
sexed_duckies = duckies_litters.exclude(sex=2)
duckypup_strains = []
for ducky_pup in sexed_duckies:
    duckypup_strains.append(ducky_pup.strain_description)
duckypups_np = np.array(duckypup_strains)
duckypupstrains_unique = np.unique(duckypups_np)

# I actually want to get all mice with progeny, and every combination of them


all_litters = colony.models.Litter.objects.filter()
moms_dict =  all_litters.values('mother').distinct()
dads_dict =  all_litters.values('father').distinct()
momid_list = []
for mom in moms_dict:
    momid_list.append(mom['mother'])
moms_qset = colony.models.Mouse.objects.filter(id__in=momid_list)


parents_list = []
all_litters = colony.models.Litter.objects.filter()
for litter in all_litters:
    mom = litter.mother
    dad = litter.father
    parents_list.append([mom,dad])