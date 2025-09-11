from rest_framework import serializers

from myapp.models import LinkCollection, LinkCollectionThumbnail
from .link import LinkSerializer
from .user import UserSerializer


class LinkCollectionThumbnailSerializer(serializers.ModelSerializer):
    class Meta:
        model = LinkCollectionThumbnail
        fields = ('image_url',)

class LinkCollectionSerializer(serializers.ModelSerializer):
    links = LinkSerializer(many=True, read_only=True)
    owner = UserSerializer(read_only=True)
    thumbnail = LinkCollectionThumbnailSerializer(read_only=True)
    is_bookmarked = serializers.BooleanField(read_only=True)
    is_liked = serializers.BooleanField(read_only=True)
    total_likes = serializers.IntegerField(source='likes_count', read_only=True)
    view_counts = serializers.IntegerField(source='views_count', read_only=True)
    active_share_link = serializers.SerializerMethodField()
    thumbnail_image_url = serializers.URLField(write_only=True, required=False, allow_null=True)

    def get_active_share_link(self, obj):
        if obj.share_uuid is not None and not obj.is_expired:
            return f"http://localhost:8080/collections/{obj.share_uuid}"

        return None

    class Meta:
        model = LinkCollection
        fields = ('id', 'title', 'owner', 'description', 'is_public', 'created_at', 'updated_at', 'links',
                  'is_bookmarked', 'is_liked', 'total_likes', 'view_counts', 'active_share_link', 'expire_date',
                  'thumbnail', 'thumbnail_image_url')
        read_only_fields = ('created_at', 'updated_at', 'total_likes', 'view_counts')

class LinkCollectionListSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)
    thumbnail = LinkCollectionThumbnailSerializer(read_only=True)

    class Meta:
        model = LinkCollection
        fields = ('id', 'title', 'owner', 'description', 'is_public', 'thumbnail')
        read_only_fields = ('created_at', 'updated_at',)
