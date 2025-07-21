from django.db import models

# Create your models here.
class brand(models.Model):
    brand_id = models.AutoField(primary_key=True)
    brand_name = models.CharField(max_length=40)

    def __str__(self):
        return self.brand_name


# class staticobject(models.Model):
#     staticobject_id = models.AutoField(primary_key=True)
#     staticobject_name = models.CharField(max_length=20)

class object_coordinate(models.Model):
    object_coordinate_x = models.FloatField()
    object_coordinate_y = models.FloatField()
    brand = models.ForeignKey(brand, on_delete=models.CASCADE, db_column="brand_id")
    # staticobject = models.ForeignKey(staticobject, on_delete=models.CASCADE, db_column="staticobject_id", null=True)

#ips 사진 업로드
class Photo(models.Model):
    image = models.ImageField(upload_to='media/')

class SensorData(models.Model):
    time = models.DateTimeField(auto_now_add=True)
    x = models.FloatField()
    y = models.FloatField()
    z = models.FloatField()
    x1 = models.FloatField()
    y1 = models.FloatField()
    z1 = models.FloatField()

    def __str__(self):
        return f"SensorData at {self.time}"

class SensorDataMagnet(models.Model):
    time = models.DateTimeField(auto_now_add=True)
    x1 = models.FloatField()
    y1 = models.FloatField()
    z1 = models.FloatField()

    def __str__(self):
        return f"SensorData at {self.time}"


## Lee GyuMin
# GPS 데이터
class GPSData(models.Model):
    latitude = models.FloatField()
    longitude = models.FloatField()
    timestamp = models.DateTimeField()
    average_speed = models.FloatField(null=True)

    def __str__(self):
        return f"Lat: {self.latitude}, Lon: {self.longitude}, Timestamp: {self.timestamp}, Average_Speed: {self.average_speed}"

class AvgSpeed(models.Model):
    avg_speed = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.avg_speed} km/h recorded at {self.timestamp}"