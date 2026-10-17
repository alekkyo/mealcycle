from rest_framework import serializers

from accounts.models import User


class MeSerializer(serializers.ModelSerializer):
    trial_ends_at = serializers.DateTimeField(source="profile.trial_ends_at")
    trial_active = serializers.BooleanField(source="profile.trial_is_active")

    class Meta:
        model = User
        fields = ["email", "trial_ends_at", "trial_active"]
