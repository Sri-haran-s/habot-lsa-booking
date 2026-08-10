from django.contrib import admin
from .models import Parent, LSAProfile, BookingRequest


@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "email", "created_at"]
    search_fields = ["name", "email"]
    list_filter = ["created_at"]


@admin.register(LSAProfile)
class LSAProfileAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "email", "experience_years", "is_active", "created_at"]
    search_fields = ["name", "email"]
    list_filter = ["is_active", "created_at"]


@admin.register(BookingRequest)
class BookingRequestAdmin(admin.ModelAdmin):
    list_display = ["id", "parent", "lsa", "start_time", "end_time", "status", "created_at"]
    list_filter = ["status", "created_at"]
    search_fields = ["parent__name", "lsa__name"]
    date_hierarchy = "start_time"
