from prospects.models import Prospect 
from dbindexer.api import register_index
register_index(Prospect, {'email': 'iexact'})