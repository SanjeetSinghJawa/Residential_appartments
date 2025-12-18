from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone # Import timezone for date/time handling

# Create your models here.
# Create your models here.
class UserDetails(models.Model):
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=100)
    flat_number = models.CharField(max_length=100)
    role = models.CharField(max_length=100)

    def __str__(self):
        return self.email

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
    reported_by_id = models.ForeignKey(UserDetails, on_delete=models.CASCADE)
    # Add an image field, files will be stored in a subfolder named 'issue_images' inside MEDIA_ROOT
    image = models.ImageField(upload_to='issue_images/', blank=True, null=True)

    def __str__(self):
        return self.title
    
# New model for site-wide notifications
class SiteNotification(models.Model):
    # 'New Issue Raised', 'Voting Started', 'Issue Resolved'
    title = models.CharField(max_length=100) 
    # 'Leaking pipe reported in Block A.', etc.
    message = models.TextField() 
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Order by newest first
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def time_since_created(self):
        # Helper method to display time since creation (e.g., "2 mins ago")
        now = timezone.now()
        diff = now - self.created_at
        if diff.days == 0:
            if diff.seconds < 60:
                return f"{diff.seconds} seconds ago"
            elif diff.seconds < 3600:
                return f"{diff.seconds // 60} mins ago"
        elif diff.days == 1:
            return "Yesterday"
        return self.created_at.strftime("%b %d, %Y") # Fallback for older dates

