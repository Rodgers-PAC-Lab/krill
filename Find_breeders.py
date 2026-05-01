#   RIGHT NOW, THIS IS NOT ACTUAL FUNCTIONING CODE!!!
# Instead, follow these steps in a terminal:
# Go to inner krill directory
# Activate krill conda env
# python manage.py shell
# THEN you can paste the following.


import colony.models
import datetime
import pandas

def mice_in_cage(cage_name):
    # Give a list with info about the specified cage.
    cage = colony.models.Cage.objects.get(name=cage_name)
    mice = colony.models.Mouse.objects.filter(cage=cage.id)
    cagedata_l=[cage.name,cage.auto_needs_message(),cage.dar_id,mice.count(),cage.sticker]
    return cagedata_l
def get_weaning_dates():
    weaning_data = []
    for x in born:
        sticker = colony.models.Cage.objects.filter(name = x)[0].sticker
        # print(x, "    ", cage)
        # sticker = cage[0].sticker
        earliest_wean = x.dob + datetime.timedelta(days=19)
        latest_wean = x.dob + datetime.timedelta(days=24)
        maturity = x.dob + datetime.timedelta(days=7*5)
        results = x.breeding_cage, sticker, x.dob,earliest_wean,latest_wean,maturity
        weaning_data.append(results)
    return weaning_data

# Finds active breeding cages
breeding = colony.models.Litter.objects.filter(
    date_weaned=None, breeding_cage__defunct=False)
born = breeding.exclude(dob = None)
litter_dates = breeding.values("breeding_cage__name","date_mated","dob")

weaning_data = get_weaning_dates()
wean_tbl = pandas.DataFrame(weaning_data,
    columns=['Cage', 'Sticker','DoBirth','Early wean', 'Late wean','Sexual maturity'])
wean_tbl = wean_tbl.set_index('Cage')


all_cages = colony.models.Cage.objects.filter(defunct=False)
# all_cages.prefetch_related('mouse_set')
# relevant_genesets = [cage.relevant_genesets for cage in all_cages.all()]
all_mice = colony.models.Mouse.objects.filter(sack_date__isnull=True)
# one = all_cages[28]
# MP_cages = []
# for cage in all_cages.all():
#     cage_mice = cage.mouse_set.all()
#     cage_printgs = cage.printable_relevant_genesets
#     if 'Tfam-flox' in cage_printgs:
#         MP_cages.append(cage)

MP_breeders_l = []
for mouse in all_mice:
    # mgenes_l = mouse.mousegene_set.all()
    mgenotype = mouse.genotype
    # 0 is male, 1 is F, 2 is ?
    msex = mouse.sex
    m_age = mouse.age()
    m_cage = mouse.cage
    if m_cage is not None:
        m_csticker = m_cage.sticker
    else:
        m_csticker = "No sticker"
    if mgenotype=="DAT-Ires-Cre(+/-); Tfam-flox(+/+)" and msex==0:
        MP_breeders_l.append([mouse, msex, m_age,
            mgenotype, "MitoPark father", m_cage, m_csticker])
    elif mgenotype=="Tfam-flox(+/+)" and msex==1:
        MP_breeders_l.append([mouse, msex, m_age,
            mgenotype, "Tfam +/+ mother", m_cage, m_csticker,])
MP_breeding_df = pandas.DataFrame(MP_breeders_l)
MP_breeding_df = MP_breeding_df.rename(columns={
    0 : "mouse_id",
    1 : "sex",
    2 : "age",
    3 : "genotype",
    4 : "notes",
    5 : "cage",
    6 : "sticker",
})
MP_breeding_df = MP_breeding_df.set_index('mouse_id')
MP_breeding_df = MP_breeding_df.sort_values('sex')
MP_breeding_df.to_csv('MitoPark breeders.csv')