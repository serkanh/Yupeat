from django.db import models
    
class Recipe(models.Model):
    name = models.CharField(max_length=500)
    image = models.FileField(upload_to='uploads/%Y/%m/%d', blank=True, null=True)
    image_attribution = models.CharField(max_length=1000,blank=True, null=True)
    ingrfull = models.TextField(max_length=20000, blank=True, null=True)
    items = models.TextField(max_length=20000, blank=True, null=True)
    dirfull = models.TextField(max_length=10000, blank=True, null=True)
    serv = models.IntegerField(blank=True, null=True)
    readyin = models.IntegerField(blank=True, null=True)
    cooktime = models.IntegerField(blank=True, null=True)
    preptime = models.IntegerField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now=True)
    attribution = models.CharField(max_length=1000,blank=True, null=True)
    
    igrfull_styled = models.TextField(max_length=20000, blank=True, null=True)
    
    @property
    def filename(self):
        return self.file.name.rsplit('/', 1)[-1]

class Meal(models.Model):
    name = models.CharField(max_length=500)
    recipe = models.ForeignKey(Recipe, null=True, blank=True)
    