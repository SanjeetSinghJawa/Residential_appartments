from django.db import models
from django.contrib.auth.models import User

# Create your models here.
# Create your models here.
class user_details(models.Model):
    
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=100)
    flat_number = models.CharField(max_length=100)
    role = models.CharField(max_length=100)

class Issue(models.Model):
    STATUS_CHOICES = [
        ('Open', 'Open'),
        ('In Review', 'In Review'),
        ('Resolved', 'Resolved'),
    ]
    title = models.CharField(max_length=100)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Open')
    reported_date = models.DateField(auto_now_add=True)
    reported_by = models.ForeignKey(User, on_delete=models.CASCADE)
    # Add an image field, files will be stored in a subfolder named 'issue_images' inside MEDIA_ROOT
    image = models.ImageField(upload_to='issue_images/', blank=True, null=True)

    def __str__(self):
        return self.title
