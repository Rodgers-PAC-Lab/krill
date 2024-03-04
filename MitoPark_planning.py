import colony.models
import pandas

Lucas_cages = colony.models.Cage.objects.filter(proprietor_id=8)
M_1123=Lucas_cages[20]
M1123_mice=colony.models.Mouse.objects.filter(cage=M_1123)

#Cre_Tflox_cages = colony.models.Cage.objects.filter(relevant_genesets=[('DAT-Ires-Cre', 'Tfam-flox')])
Living_mice = colony.models.Mouse.objects.filter(sacked=False)

qset_w_genes = mouse_1101.mousegene_set.all()

all_mousegenes=colony.models.MouseGene.objects.filter()
all_mousegenes[1]
all_mousegenes[1].zygosity
all_mousegenes[1].mouse_name
all_mousegenes[1].gene_name

all_genes = colony.models.Gene.objects.filter()
Cre_gene = all_genes.filter(name="DAT-Ires-Cre").get()

all_litters = colony.models.Litter.objects.filter()


# Pseudocode to look at mouse sex in the db for bias over time...
# Want to separate by breeding cross and/or by breeding pair
# Colony_pups = mice born from our pairs, not ordered from outside
# Optional date critera and/or particular breeding pair criteria
# Pup_genesets = unique genesets in colony_pups
# For each geneset in pup_genesets:
#   M = count mouses in colony_pups where mouse_geneset=geneset and sex=M
#   F = Same but for F
# M_percentage = M/colony_pups * 100 (repeat for F)

# An array of allll the breeding pairs we've had, as mom, dad, and list of litter IDs if I feel ambitious

