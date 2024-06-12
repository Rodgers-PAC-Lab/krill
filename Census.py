import colony.models
import pandas

allcages = colony.models.Cage.objects.filter(defunct = False)

cage_data = []

for cage in allcages:
    cage_data.append([cage.proprietor,cage.name,cage.sticker,cage.n_mice(),cage.dar_id])
census_df = pandas.DataFrame(cage_data, columns=('Proprietor','Name','sticker','Number_mice','DAR_ID'))