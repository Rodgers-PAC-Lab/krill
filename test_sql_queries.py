"""

select_related is for tables (i.e., litter) and each must be specified
prefetch_related is for reverse foreign key (i.e., mouse_set)
Any .filter operation will not take advantage of prefetch
You can deal with that with a Prefetch object, but it seems a little
clunky, it needs to be before the prefetch_related, and I think it works
only for the exact filter. But it can put it in an attr (impure_mice).
    prefetch_related(
        Prefetch('mouse_set', 
            queryset=colony.models.Mouse.objects.filter(pure_breeder=False), 
            to_attr='impure_mice'))
"""

from django.test.client import RequestFactory
from django.conf import settings
settings.DEBUG = True
from django.db import connection
import colony.views
import colony.models




def test1():
    """Test of SQL queries required for type and relevant genesets"""
    cages = colony.models.Cage.objects.filter(defunct=False)

    cages = cages.prefetch_related('mouse_set').\
        prefetch_related('specialrequest_set').\
        prefetch_related('specialrequest_set__requester').\
        prefetch_related('specialrequest_set__requestee').\
        prefetch_related('mouse_set__litter').\
        prefetch_related('mouse_set__user').\
        prefetch_related('mouse_set__genotype').\
        prefetch_related('litter__mouse_set').\
        prefetch_related('litter__father__mousegene_set').\
        prefetch_related('litter__mother__mousegene_set').\
        prefetch_related('litter__father__mousegene_set__gene_name').\
        prefetch_related('litter__mother__mousegene_set__gene_name').\
        prefetch_related('mouse_set__mousegene_set').\
        prefetch_related('mouse_set__mousegene_set__gene_name').\
        select_related('litter', 'litter__father', 'litter__mother', 
            'proprietor', 'litter__proprietor')

    for cage in cages.all():
        if hasattr(cage, 'litter') and cage.litter:
            cage.type_of_cage
            cage.printable_relevant_genesets

def test2():
    """Test for loading the whole page"""
    v = colony.views.census_by_genotype

    factory = RequestFactory()
    request = factory.get('/colony/census_by_genotype.html')

    response = v(request)
    #~ tr = response.render()

    #~ print tr.content

def test3():
    """Test simulating the whole render to identify bottleneck"""
    # non-defunct cages
    qs = colony.models.Cage.objects.filter(defunct=False, proprietor__name__icontains='Chris')
    
    # Now select related
    qs = qs.prefetch_related('mouse_set').\
        prefetch_related('specialrequest_set').\
        prefetch_related('specialrequest_set__requester').\
        prefetch_related('specialrequest_set__requestee').\
        prefetch_related('mouse_set__litter').\
        prefetch_related('mouse_set__user').\
        prefetch_related('mouse_set__genotype').\
        prefetch_related('litter__mouse_set').\
        prefetch_related('litter__father__mousegene_set').\
        prefetch_related('litter__mother__mousegene_set').\
        prefetch_related('litter__father__mousegene_set__gene_name').\
        prefetch_related('litter__mother__mousegene_set__gene_name').\
        prefetch_related('mouse_set__mousegene_set').\
        prefetch_related('mouse_set__mousegene_set__gene_name').\
        select_related('litter', 'litter__father', 'litter__mother', 
            'proprietor', 'litter__proprietor')
    
    # Extract relevant genesets
    relevant_genesets = [cage.relevant_genesets for cage in qs.all()]
    unique_relevant_genesets = []
    for rg in relevant_genesets:
        for srg in rg:
            tsrg = tuple(srg)
            if tsrg not in unique_relevant_genesets:
                unique_relevant_genesets.append(tsrg)
    
    # Sort by first gene, then number of genes
    unique_relevant_genesets = sorted(unique_relevant_genesets, 
        key=lambda v: (v[0] if len(v) > 0 else '', len(v)))

    # Iterate once over cages and group by geneset
    geneset2cage_l = {}
    for cage in qs.all():
        for geneset in cage.relevant_genesets:
            if geneset in geneset2cage_l:
                geneset2cage_l[geneset].append(cage)
            else:
                geneset2cage_l[geneset] = [cage]

    # Now refactor
    sorted_by_geneset = []
    for geneset in unique_relevant_genesets:
        sorted_by_geneset.append({
            'geneset': geneset,
            'dname': (' x '.join(geneset)) if len(geneset) > 0 else 'WT',
            'cage_l': geneset2cage_l[geneset]
        })
    return
    
    sorted_by_geneset = []
    for geneset in unique_relevant_genesets:
        cage_l = []
        
        # This loop triggers a lot of SQL queries
        # I think it's just evaluating cage which has to happen anyway
        for cage, relevant_geneset in zip(qs.all(), relevant_genesets):
            if geneset in relevant_geneset:
                cage_l.append(cage)
        
        sorted_by_geneset.append({
            'geneset': geneset,
            'dname': (' x '.join(geneset)) if len(geneset) > 0 else 'WT',
            'cage_l': cage_l,
        })

def test4():
    qs = colony.models.Cage.objects.filter(defunct=False, proprietor__name__icontains='Chris')
    qs = qs.prefetch_related('mouse_set').\
        prefetch_related('specialrequest_set').\
        prefetch_related('specialrequest_set__requester').\
        prefetch_related('specialrequest_set__requestee').\
        prefetch_related('mouse_set__litter').\
        prefetch_related('mouse_set__user').\
        prefetch_related('mouse_set__genotype').\
        prefetch_related('litter__mouse_set').\
        prefetch_related('litter__father__mousegene_set').\
        prefetch_related('litter__mother__mousegene_set').\
        prefetch_related('litter__father__mousegene_set__gene_name').\
        prefetch_related('litter__mother__mousegene_set__gene_name').\
        prefetch_related('mouse_set__mousegene_set').\
        prefetch_related('mouse_set__mousegene_set__gene_name').\
        select_related('litter', 'litter__father', 'litter__mother', 
            'proprietor', 'litter__proprietor')    
    
    
    for cage in qs.all():
        cage

cq0 = len(connection.queries)

test2()

cq1 = len(connection.queries)
print cq1 - cq0


