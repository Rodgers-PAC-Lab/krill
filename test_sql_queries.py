from django.test.client import RequestFactory
from django.conf import settings
settings.DEBUG = True
from django.db import connection
import colony.views
import colony.models


cq0 = len(connection.queries)
v = colony.views.census_by_genotype

factory = RequestFactory()
request = factory.get('/colony/census_by_genotype.html')

response = v(request)
#~ tr = response.render()

#~ print tr.content
cq1 = len(connection.queries)
print cq1 - cq0