from django.contrib import admin
from .models import UserDetails,Issue, SiteNotification
admin.site.register(Issue)
admin.site.register(SiteNotification)

# Register your models here.
admin.site.register(UserDetails)