import colony.models
import pandas
import numpy as np

# Get people to be able to code in the proprietor
# people = colony.models.Person.objects.values_list()
# for person in people:
#     print(person[0:2])

# Cedric = 5, Eliana = 6, Lucas = 8
Lucas_cages = colony.models.Cage.objects.filter(proprietor_id=8)
# M_1123=Lucas_cages[20]
# M1123_mice=colony.models.Mouse.objects.filter(cage=M_1123)



Cre_Tflox_cages = colony.models.Cage.objects.filter(relevant_genesets=[('DAT-Ires-Cre', 'Tfam-flox')])
# qs = colony.models.Cage.objects.filter(defunct=False)
# attributes = qs.__dict__

Living_mice = colony.models.Mouse.objects.filter(sack_date__isnull=True, cage__isnull=False)

#Living_mice = Living_mice.prefetch_related('mousegene_set').prefetch_related('litter')
# Cre_mice_l = []
# for mouse in Living_mice:
#     if mouse.mousegene_set.exists():
#         for mg in mouse.mousegene_set.all():
#             if mg.gene_name.name == "DAT-Ires-Cre":
#                 gene = mg.gene_name.name
#                 zygosity = mg.zygosity
#                 age = mouse.age()
#                 cage = mouse.cage
#                 Cre_mice_l.append([mouse,age,cage,gene,zygosity])
# Cre_mice_df = pandas.DataFrame(Cre_mice_l,columns = ['Mouse','age','cage','gene','zygosity'])

all_MPgene_mice = []
for mouse in Living_mice:
    if mouse.mousegene_set.exists():
        mouses_geneset = []
        for mg in mouse.mousegene_set.all():
            mouses_geneset.append(mg.gene_name.name)

        if "DAT-Ires-Cre" in mouses_geneset or 'Tfam-flox' in mouses_geneset:
            all_MPgene_mice.append([mouse,mouse.genotype])
all_MPgene_mice = pandas.DataFrame(all_MPgene_mice,columns=['Mouse','genotype'])
MPgene_mice_l = []
for mouse in all_MPgene_mice['Mouse']:
    Cre_zygosity = 'NA'
    TFlox_zygosity = 'NA'
    for mg in mouse.mousegene_set.all():
        if mg.gene_name.name =="DAT-Ires-Cre":
            Cre_zygosity = mg.zygosity
        elif mg.gene_name.name == 'Tfam-flox':
            TFlox_zygosity = mg.zygosity
        else: print("EXTRA UNKNOWN GENE, HALT!!")
    MPgene_mice_l.append([mouse,mouse.age(),mouse.sex, mouse.cage,Cre_zygosity,TFlox_zygosity])

MPgene_mice_df = pandas.DataFrame(MPgene_mice_l,columns = ['Mouse','age', 'sex','cage','Cre_zygosity','TFlox_zygosity'])

# MPgene_mice_df['breeding_notes']=''
# for i in np.arange(0,len(MPgene_mice_df)):
#     #Look for potential Mitopark dads
#     mouse = MPgene_mice_df.loc[i]
#     if mouse['sex'] == 0 and mouse['Cre_zygosity'] == '+/-' and mouse['TFlox_zygosity'] == '+/-':
#         #This below doesn't actually work for some reason
#         mouse['breeding_notes'] = 'Potential mitopark dad'

MPdads = MPgene_mice_df.query('sex==0 and Cre_zygosity=="+/-" and TFlox_zygosity=="+/-"')
MPgene_mice_df.to_csv('MPgene_mice.csv')


all_mousegenes=colony.models.MouseGene.objects.filter()
all_mousegenes[1]
all_mousegenes[1].zygosity
all_mousegenes[1].mouse_name
all_mousegenes[1].gene_name

all_genes = colony.models.Gene.objects.filter()
Cre_gene = all_genes.filter(name="DAT-Ires-Cre").get()
FAD_gene = all_genes.filter(name="5xFAD").get()

#mouse1.mousegene_set.filter(gene_name_id=1).get().zygosity

parents_l = []
all_litters = colony.models.Litter.objects.filter()
for litter in all_litters:
    mom = litter.mother
    dad = litter.father
    if [dad, mom] in parents_l:
        continue
    else:
        parents_l.append([dad, mom])