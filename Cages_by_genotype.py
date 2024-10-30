import colony.models
import pandas

def mice_in_cage(cage_name):
    cage = colony.models.Cage.objects.get(name=cage_name)
    mice = colony.models.Mouse.objects.filter(cage=cage.id)
    cagedata_l=[cage.name,cage.auto_needs_message(),cage.dar_id,mice.count(),cage.sticker]
    return cagedata_l



Living_mice = colony.models.Mouse.objects.filter(sack_date__isnull=True, cage__isnull=False)

all_FAD_mice = []
for mouse in Living_mice:
    if mouse.mousegene_set.exists():
        mouses_geneset = []
        for mg in mouse.mousegene_set.all():
            mouses_geneset.append(mg.gene_name.name)

        if "5xFAD" in mouses_geneset:
            all_FAD_mice.append([mouse,mouse.genotype])
all_FAD_mice = pandas.DataFrame(all_FAD_mice, columns=['Mouse','genotype'])

FAD_mice_l = []
for mouse in all_FAD_mice['Mouse']:
    FAD_zygosity = 'NA'
    for mg in mouse.mousegene_set.all():
        if mg.gene_name.name =="5xFAD":
            FAD_zygosity = mg.zygosity
        else: print("EXTRA UNKNOWN GENE, HALT!!")
    FAD_mice_l.append([mouse,mouse.age(),mouse.sex, mouse.cage,FAD_zygosity])

FAD_mice_df = pandas.DataFrame(FAD_mice_l,columns = ['Mouse','age', 'sex','cage','FAD_zygosity'])

FAD_cages = FAD_mice_df['cage'].unique()

all_cagedata=[]
for x in FAD_cages:
    results=mice_in_cage(x)
    all_cagedata.append(results)

FAD_cage_df = pandas.DataFrame(all_cagedata)