from rest_framework import serializers

from myapp.models import Bookmark
from .collection import LinkCollectionListSerializer
from .user import UserSerializer


class BookmarkSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)
    collections = LinkCollectionListSerializer(many=True)

    class Meta:
        model = Bookmark
        fields = '__all__'
        read_only_fields = ('owner',)
