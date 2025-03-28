from django.db import models

# Create your models here. 
# test push
class Restaurant(models.Model):
    name = models.CharField(max_length=255)
    cuisine = models.CharField(max_length=255)
    price_range = models.CharField(max_length=10)
    rating = models.FloatField()
    reviews = models.IntegerField()
    # Store latitude and longitude as decimal numbers
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    status = models.CharField(max_length=255, blank=True, null=True)
    tags = models.JSONField(default=list, blank=True)

    def __str__(self):
        return self.name

