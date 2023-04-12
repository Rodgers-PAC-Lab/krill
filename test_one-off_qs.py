# import django
# import os
# import sys
#
# django_project_path = os.path.expanduser('~/dev/krill/krill')
# if django_project_path not in sys.path:
#     sys.path.append(django_project_path)
#
# # Set environment variable
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "HeroMouseColony.settings")
#
# # Setup django
# django.setup()
# qs = Mouse.objects.filter(sex=0, sack_date__isnull=True).all()
#
# import colony.models
#
#
#     for x in cage_list:
#         cage = colony.models.Cage.objects.get(name=x)
#         mice = colony.models.Mouse.objects.filter(cage=cage.id)
#         print(cage.name, cage.id,mice)

#   RIGHT NOW, THIS IS NOT ACTUAL FUNCTIONING CODE!!!
# Instead, follow these steps in a terminal:
# Go to inner krill directory
# Activate kirll conda env
# python manage.py shell
# THEN you can paste the following.


import colony.models

cage_list = ['1034-F','1035-F','1040-F','1041-F','1042-F','1044-F','1044-M',
             '1045-M','1046-F', '1046-M', '1047-F', '1047-M', '1048-F',
             '1049','1049-F','1049-M','1070','1071'
             ]

def mice_in_cage(cage_name):
    cage = colony.models.Cage.objects.get(name=cage_name)
    mice = colony.models.Mouse.objects.filter(cage=cage.id)
    cagedata_l=[cage.name,cage.auto_needs_message(),cage.dar_id,mice.count(),cage.sticker]
    return cagedata_l

all_cagedata=[]
for x in cage_list:
    results=mice_in_cage(x)
    all_cagedata.append(results)


def find_sac_requests():
    all_cages = colony.models.Cage.objects.filter(defunct=False)
    sack_list=[]
    for cage in all_cages:
        cage_autoneeds = cage.auto_needs_message()
        if 'sack' in cage_autoneeds.lower():
            sack_list.append(cage.name)
    return sack_list

sack_list = find_sac_requests()
cages_toSack = colony.models.Cage.objects.filter(name__in=sack_list)

sack_cagedata = []
for x in cages_toSack:
    results=mice_in_cage(x)
    sack_cagedata.append(results)