from django.contrib import admin

from accounts.models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    # Plain ModelAdmin on purpose: Django's built-in UserAdmin assumes a
    # username and password forms, and our app users are passwordless.
    list_display = ("email", "is_active", "is_staff", "date_joined")
    search_fields = ("email",)
    list_filter = ("is_active", "is_staff")
    ordering = ("email",)
    fields = (
        "email",
        "is_active",
        "is_staff",
        "is_superuser",
        "groups",
        "user_permissions",
        "date_joined",
        "last_login",
    )
    readonly_fields = ("date_joined", "last_login")
    filter_horizontal = ("groups", "user_permissions")
