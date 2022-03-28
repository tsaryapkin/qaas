from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response

from .serializers import UserSerializer


@api_view(["POST"])
@permission_classes([AllowAny])
def signup(request: Request) -> Response:
    serialized = UserSerializer(data=request.data)
    if serialized.is_valid():
        serialized.save()
        return Response(serialized.data, status=status.HTTP_201_CREATED)
    return Response(serialized._errors, status=status.HTTP_400_BAD_REQUEST)
