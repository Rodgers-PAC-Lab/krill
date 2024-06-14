import colony.models
import pandas

allcages = colony.models.Cage.objects.filter(defunct = False)

cage_data = []

for cage in allcages:
    cage_data.append([cage.proprietor,cage.name,cage.sticker,cage.n_mice(),cage.dar_id])
census_df = pandas.DataFrame(cage_data, columns=('Proprietor','Name','sticker','Number_mice','DAR_ID'))
Cedric_cages = allcages.filter(proprietor='5')
# Fetch mice in the cage
qs = Cedric_cages.prefetch_related('mouse_set').\
    prefetch_related('mouse_set__mousegene_set')
for cage in allcages:
    cage_data.append([cage.proprietor,cage.name,cage.sticker,cage.n_mice(),cage.dar_id])
census_df = pandas.DataFrame(cage_data, columns=('Proprietor','Name','sticker','Number_mice','DAR_ID'))