from django.contrib import admin

from accounts.models import Profile, User


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    fields = ("trial_started_at",)


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
    inlines = (ProfileInline,)

    def get_inlines(self, request, obj):
        # Only on the edit page. On "add user" the post_save signal creates the
        # profile, and an inline would try to create a second one (IntegrityError).
        return self.inlines if obj else ()
