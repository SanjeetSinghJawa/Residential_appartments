from django.contrib import admin
from .models import UserDetails,Issue
admin.site.register(Issue)

# Register your models here.
admin.site.register(UserDetails)