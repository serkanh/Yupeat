from django.db import models

class CDN(models.Model):
    name = models.CharField(max_length=100)
    image = models.FileField(upload_to='uploads/%Y/%m/%d', blank=True, null=True)
    
    @property
    def filename(self):
        return self.file.name.rsplit('/', 1)[-1]