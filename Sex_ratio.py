import colony.models
import numpy as np
import pandas
# Get a list of all the unique breeding pairs we've had
parents_l = []
all_litters = colony.models.Litter.objects.filter()
for litter in all_litters:
    mom = litter.mother
    dad = litter.father
    if [dad, mom] in parents_l:
        continue
    else:
        parents_l.append([dad, mom])
pair7 = parents_l[7]
pair7_litters = colony.models.Litter.objects.filter(mother=pair7[1],father=pair7[0])
pair7_pups_qs = colony.models.Mouse.objects.filter(Q(litter=pair7_litters[1]) | Q(litter=pair7_litters[0]))
    pair7_pups = colony.models.Mouse.objects.filter(mother=pair7[1],father=pair7[0])

# Simplest sex check version first:
pups_by_parents = []
for pair in parents_l:
    # check if they have progeny.
    pair_litters = colony.models.Litter.objects.filter(mother=pair[1], father=pair[0])
    pair_pups=[]
    for one_litter in pair_litters:
        litter_pups = colony.models.Mouse.objects.filter(litter=one_litter)
        for pup in litter_pups:
            pair_pups.append(pup)
    pups_by_parents.append(pair_pups)
# Currently gives 33 elements, last one with actual pups is [23]
pup_sexes = []
for puplist in pups_by_parents:
    males = 0
    females = 0
    unsexed = 0
    for pup in puplist:
        if pup.sex == 0:
            males = males+1
        if pup.sex == 1:
            females = females+1
        if pup.sex == 2:
            unsexed = unsexed+1
    pup_sexes.append([males,females,unsexed])

# for i in np.arange(0,len(parents_l)):
for i in np.arange(0,24):
    print(parents_l[i], 'male ',pup_sexes[i][0],'female ',pup_sexes[i][1], 'unsexed',pup_sexes[i][2])
for i in np.arange(0, 24):
    print(parents_l[i][0], 'dad genotype ', parents_l[i][0].genotype,parents_l[i][1], 'mom genotype ', parents_l[i][1].genotype,
          'male ',pup_sexes[i][0],'female ',pup_sexes[i][1], 'unsexed',pup_sexes[i][2])

# Describe characteristics like target genotype, progeny, sex ratio, etc
parent_descriptors_l = []
parent_descriptor_labels = ['Mom_ID','Mom_strain','Mom_genotype',
                            'Dad_ID','Dad_strain','Dad_genotype',
                            'Litter_ID','Litter_cage','Litter_genotype',
                            'Males','Females']




all_litters = colony.models.Litter.objects.filter()
# L_1050 = all_litters[0] #no get(), gives object not queryset huh
#
# # QSet with all mice in litter but also like, not in a useful form?
# # It's a QS of... tuples????
# L_1050_mice = L_1050.mouse_set.values_list()
# # Gets numerical mouse ID of first mouse in the litter.
# # Use this syntax to iterate over litter and grab a QS of all mice objects if needed.
# L_1050_mouseid = L_1050.mouse_set.values_list()[0][0]
#
# all_litters = colony.models.Litter.objects.filter()
# all_genotypes = all_litters.values('target_genotype').distinct()
# # all_genotypes gives a queryset, but again it's a QS of dicts
# # THIS gets a string of the genotype finally
# gtype1 = all_genotypes[0]['target_genotype']
# FAD_litters = colony.models.Litter.objects.filter(target_genotype = gtype1)
# FAD_moms = FAD_litters.values('mother').distinct()
# duckies_mom = colony.models.Mouse.objects.filter(id=FAD_moms[6]['mother']).get()
# duckies_litters = duckies_mom.progeny
# sexed_duckies = duckies_litters.exclude(sex=2)
# duckypup_strains = []
# for ducky_pup in sexed_duckies:
#     duckypup_strains.append(ducky_pup.strain_description)
# duckypups_np = np.array(duckypup_strains)
# duckypupstrains_unique = np.unique(duckypups_np)
#
# # I actually want to get all mice with progeny, and every combination of them
#
#
# all_litters = colony.models.Litter.objects.filter()
# moms_dict =  all_litters.values('mother').distinct()
# dads_dict =  all_litters.values('father').distinct()
# momid_list = []
# for mom in moms_dict:
#     momid_list.append(mom['mother'])
# moms_qset = colony.models.Mouse.objects.filter(id__in=momid_list)


