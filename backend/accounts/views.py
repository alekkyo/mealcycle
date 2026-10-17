from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.serializers import MeSerializer


class MeView(APIView):
    """The logged-in user's account and trial status."""

    def get(self, request):
        return Response(MeSerializer(request.user).data)
