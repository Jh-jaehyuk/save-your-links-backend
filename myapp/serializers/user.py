from django.contrib.auth.models import User
from rest_framework import serializers

from myapp.models import UserAvatar


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('username', 'email', 'is_staff')
        read_only_fields = ('is_staff',)

class UserAvatarSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserAvatar
        fields = ('image_url',)

class UserinfoSerializer(serializers.ModelSerializer):
    avatar = UserAvatarSerializer(read_only=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'is_staff', 'avatar')
        read_only_fields = ('is_staff', 'email')
