from django.contrib import admin

from .models import UserProfile, DailyEntry

admin.site.register(UserProfile)
admin.site.register(DailyEntry)
