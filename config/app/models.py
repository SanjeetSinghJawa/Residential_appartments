from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone # Import timezone for date/time handling

# Create your models here.
class UserDetails(models.Model):
    full_name = models.CharField(max_length=200, null=True, blank=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=100)
    flat_number = models.CharField(max_length=100)
    role = models.CharField(max_length=100)

    def __str__(self):
        return self.full_name if self.full_name else self.email
    
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
    image = models.ImageField(upload_to='issue_images/', blank=True, null=True)

    def __str__(self):
        return self.title
    
class Solution(models.Model):
    title = models.CharField(max_length=150)
    description = models.TextField()
    # Link back to the issue it solves
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name='solutions')
    # Link back to the user who suggested it
    suggested_by = models.ForeignKey(UserDetails, on_delete=models.CASCADE)
    upvotes = models.IntegerField(default=0)
    downvotes = models.IntegerField(default=0)
    suggested_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50, default='Suggested') # e.g., Suggested, In Progress, Accepted

    def __str__(self):
        return f"{self.title} for Issue: {self.issue.title}"
    
# New model for site-wide notifications
class SiteNotification(models.Model):
    title = models.CharField(max_length=100) 
    message = models.TextField() 
    created_at = models.DateTimeField(auto_now_add=True)
    
    # NEW: Add a link back to the issue that caused the notification
    # Set blank=True, null=True because some notifications might be generic (e.g., 'Welcome')
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, null=True, blank=True) 

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    # ... time_since_created helper method ...
    def time_since_created(self):
        now = timezone.now()
        diff = now - self.created_at
        if diff.days == 0:
            if diff.seconds < 60:
                return f"{diff.seconds} seconds ago"
            elif diff.seconds < 3600:
                return f"{diff.seconds // 60} mins ago"
        elif diff.days == 1:
            return "Yesterday"
        return self.created_at.strftime("%b %d, %Y")
