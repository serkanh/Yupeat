import csv  
import string
import time

from fractions import Fraction
from google.appengine.api import memcache
from items.models import Item

class structureIngredient():
    """Identifies relevant terms (item, quantity, unit) in list of ingredients"""

    def __init__(self):
        self.items = []
        self.unit = ''
        self.quantity = ''
        self.row = {}
    
    def fooddict_subset(self,f,word,food):
        """Returns subset of the food dictionary"""
        found = False
        
        try:
            for a in f[word]: food.append(a)
            found = True
        except KeyError:
            pass
        
        return food
    
    def is_number_token(self,s):
        try:
            num = float(Fraction(s))
            return True
        except ValueError:
            try:
                float(s)
                return True
            except ValueError:
                return False
    
    def is_unit_token(self, word):
        f = cached_unit_dict()
        if word in f:
            self.unit = word
            return True
        return False
    
    def is_food_token(self,word,fooddict):
        """ store food terms from ingredient row """
        
        w = word.encode('ascii', 'ignore')
        wn = str(w)
        w = wn.translate(string.maketrans("",""), string.punctuation)
        
        found_foods = []
        
        for row in fooddict:
            
            i = '+'+w.replace(' ', '+')+'+'
            r = '+'+row.replace(' ','+')+'+'
            
            #r = row in dictionary
            #i = ingredient phrase
            compare = [r, i]
            
            substr = long_substr(compare)
            
            #substr = suffixTree(compare)
            
            start=substr.find('+')
            end=substr.rfind('+')
            
            if len(substr[start+1:end]) == len(row):
                whole_word_match = True
            else:
                whole_word_match = False
                
            if len(substr[start+1:end]) > 2 and whole_word_match:
                found_foods.append(substr[start+1:end].replace('+',' '))
        
        
        sort_key = lambda s: (-len(s), s)
        found_foods.sort(key=sort_key)
        
        self.items = found_foods
        
    def get_tokens(self, ingr_row):
        """
        Loop through ingredient row, find unit, quantity and item
        """
        
        f = cached_dict()
        found_foods = []
        line = 0
        
        xingr_row = ingr_row.lower().replace(',','')
        
        for ingr in xingr_row.split('\r\n'):
            self.clear()
            food = []
            for word in ingr.split():
                fooddict = self.fooddict_subset(f,word,food)
                found = self.is_unit_token(word)
                if not found: 
                    found = self.is_number_token(word)
                    if found: self.quantity = word
            
            self.is_food_token(ingr,food)
            self.row[line] = {'quantity':self.quantity, 'unit':self.unit, 'ingredient':self.items} 
            line += 1
            
    def clear(self):
        self.items = []
        self.unit = ''
        self.quantity = ''
    
"""
Helper methods
"""
def long_substr(data):
        """Find longest matching term"""
        substr = ''
        if len(data) > 1 and len(data[0]) > 0:
            for i in range(len(data[0])):
                for j in range(len(data[0])-i+1):
                    if j > len(substr) and all(data[0][i:i+j] in x for x in data):
                        substr = data[0][i:i+j]
        return substr

def cached_dict():
    key='fdict_v3'
    
    if memcache.get(key) != None:
        return memcache.get(key)
    else:
        item_list = getItemList()
        val = {}
        for row in item_list: 
           for word in row.split():
               if word in val: 
                   food_word_array = val[word.rstrip('\r\n')]
                   food_word_array.append(row.rstrip('\r\n'))
               else:
                   val[word.rstrip('\r\n')]=[row.rstrip('\r\n')]
        
        memcache.delete(key)
        if not memcache.add(key, val):
            logging.error("Memcache set failed.")
        return val

def cached_unit_dict():
    key='udict'
    
    if memcache.get(key) != None:
        return memcache.get(key)
    else:
        f = open('./itemparser/units.txt', 'r')
        val = {}
        for row in f:
            if row in val: pass
            else: val[row.rstrip('\r\n')]=1
    
        memcache.delete(key)
        if not memcache.add(key, val):
            logging.error("Memcache set failed.")
        return val
    
def getItemList():
    arr = []
    item_list = list(Item.objects.values('name'))
    for k in item_list:
        if k['name'] not in arr:
            arr.append(k['name'])
         
    return arr 
    