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

    """
        prefetch_related('mouse_set').\
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
    """

    for cage in cages.all():
        if hasattr(cage, 'litter') and cage.litter:
            cage.type_of_cage
            cage.printable_relevant_genesets

def test2():
    v = colony.views.census_by_genotype

    factory = RequestFactory()
    request = factory.get('/colony/census_by_genotype.html/?person=Kate')

    response = v(request)
    #~ tr = response.render()

    #~ print tr.content

cq0 = len(connection.queries)

test2()

cq1 = len(connection.queries)
print cq1 - cq0


