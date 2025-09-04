import json
import uuid

import requests
from django.conf import settings
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes
from rest_framework.response import Response

from myapp.utils import get_redis_client


@api_view(['GET'])
@authentication_classes([])
def get_kakao_redirect_uri(request):
    return Response({"uri": f"https://kauth.kakao.com/oauth/authorize?"
            f"client_id={settings.KAKAO_CLIENT_ID}&"
            f"redirect_uri={settings.KAKAO_REDIRECT_URI}&"
            f"response_type=code"})

@api_view(['POST'])
@authentication_classes([])
def kakao_login(request):
    code = request.data.get("code")

    if not code:
        return Response(status=status.HTTP_400_BAD_REQUEST, data={"error": "code is required."})

    kakao_token_uri = (f"https://kauth.kakao.com/oauth/token?"
                       f"grant_type=authorization_code&"
                       f"client_id={settings.KAKAO_CLIENT_ID}&"
                       f"redirect_uri={settings.KAKAO_REDIRECT_URI}&"
                       f"code={code}&"
                       f"client_secret={settings.KAKAO_CLIENT_SECRET}")

    kakao_token_headers = {"Content-Type": "application/x-www-form-urlencoded;charset=utf-8"}

    token_response = requests.post(kakao_token_uri, headers=kakao_token_headers)
    token_response_data = json.loads(token_response.text)

    access_token = token_response_data["access_token"]
    kakao_userinfo_uri = f"https://kapi.kakao.com/v2/user/me"

    kakao_userinfo_headers = {"Content-Type": "application/x-www-form-urlencoded;charset=utf-8",
                              "Authorization": f"Bearer {access_token}"}

    userinfo_response = requests.post(kakao_userinfo_uri, headers=kakao_userinfo_headers)
    userinfo_response_data = json.loads(userinfo_response.text)

    default_username = userinfo_response_data['properties']['nickname']
    username = default_username
    count = 0
    email = userinfo_response_data['kakao_account']['email']

    client = get_redis_client()

    try:
        user = User.objects.get(email=email)
        user_token = str(uuid.uuid4())
        client.set(user_token, user.pk, ex=3600)

        return Response({'user_token': user_token, 'is_staff': user.is_staff, 'username': user.username, 'avatar': user.avatar.image_url if user.avatar.image_url else None})

    except User.DoesNotExist:
        while User.objects.filter(username=username).exists():
            count += 1
            username = username + str(count)

        user = User(username=username, email=email)
        user.set_unusable_password()
        user.save()

        user_token = str(uuid.uuid4())
        client.set(user_token, user.pk, ex=3600)

        return Response({'user_token': user_token, 'is_staff': user.is_staff, 'username': user.username, 'avatar': user.avatar.image_url if user.avatar.image_url else None})

    except Exception as e:
        return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR, data={"error": str(e)})

@api_view(['GET'])
def get_kakao_logout_redirect_uri(request):
    return Response({"uri": f"https://kauth.kakao.com/oauth/logout?"
                            f"client_id={settings.KAKAO_CLIENT_ID}&"
                            f"logout_redirect_uri={settings.KAKAO_LOGOUT_REDIRECT_URI}"})

@api_view(['POST'])
def kakao_logout(request):
    client = get_redis_client()
    client.delete(request.token)

    return Response({"message": "logged out"})
