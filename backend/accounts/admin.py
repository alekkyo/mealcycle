from django.contrib import admin

from accounts.models import Profile, User, add_primary_email


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

    def get_readonly_fields(self, request, obj=None):
        # Changing an email needs allauth's EmailAddress kept in sync; not supported yet.
        return (*self.readonly_fields, "email") if obj else self.readonly_fields

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change:
            add_primary_email(obj)

    def get_inlines(self, request, obj):
        # Only on the edit page. On "add user" the post_save signal creates the
        # profile, and an inline would try to create a second one (IntegrityError).
        return self.inlines if obj else ()
