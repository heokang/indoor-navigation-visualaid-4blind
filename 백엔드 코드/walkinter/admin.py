from django.contrib import admin

from .models import brand,object_coordinate,Photo, GPSData

# Register your models here.
admin.site.register(brand)
admin.site.register(object_coordinate)
admin.site.register(Photo)
admin.site.register(GPSData)