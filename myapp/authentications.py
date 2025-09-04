from django.contrib.auth.models import User
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from myapp.utils import get_redis_client


class UserTokenAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get("Authorization")

        if not auth_header or not auth_header.startswith('Bearer '):
            return None

        token = auth_header.split()[1]
        redis_client = get_redis_client()
        user_id = redis_client.get(token)

        if not user_id:
            raise AuthenticationFailed('Invalid token.')

        try:
            user = User.objects.get(pk=int(user_id))

        except User.DoesNotExist:
            raise AuthenticationFailed('User not found.')

        return (user, token)
