import uuid
from datetime import timedelta

from botocore.exceptions import ClientError
from django.conf import settings
from django.db.models import Q, Count, OuterRef, Exists
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from django.db import transaction

from myapp.models import LinkCollection, LinkCollectionLike, Bookmark, LinkCollectionThumbnail
from myapp.paginations import MainPageLinkCollectionPagination
from myapp.permissions import IsOwnerOrReadOnly
from myapp.serializers import LinkCollectionSerializer
from myapp.tasks import save_view_model, delete_s3_object
from myapp.utils import get_boto3_client


class LinkCollectionView(ModelViewSet):
    queryset = (LinkCollection.objects
                .select_related('owner', 'thumbnail')
                .annotate(total_likes=Count('likes'), view_counts=Count('views'))
                .prefetch_related('links').all())
    serializer_class = LinkCollectionSerializer
    permission_classes = [IsOwnerOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()

        if user.is_authenticated:
            likes_subquery = LinkCollectionLike.objects.filter(
                collection=OuterRef('pk'),
                liker=user
            )

            bookmarks_subquery = user.bookmark.collections.filter(pk=OuterRef('pk'))

            queryset = queryset.annotate(
                is_liked=Exists(likes_subquery),
                is_bookmarked=Exists(bookmarks_subquery)
            )
        
        return queryset

    @transaction.atomic
    def perform_create(self, serializer):
        thumbnail_image_url = serializer.validated_data.pop('thumbnail_image_url', None)
        collection = serializer.save(owner=self.request.user)
        if thumbnail_image_url:
            LinkCollectionThumbnail.objects.create(collection=collection, image_url=thumbnail_image_url)

    @transaction.atomic
    def perform_update(self, serializer):
        thumbnail_image_url = serializer.validated_data.pop('thumbnail_image_url', None)
        collection = serializer.save()

        if thumbnail_image_url:
            thumbnail, created = LinkCollectionThumbnail.objects.get_or_create(collection=collection)
            old_thumbnail_key = None
            if not created and thumbnail.image_url:
                old_thumbnail_key = thumbnail.image_url.replace(settings.AWS_CLOUDFRONT_URL + '/', '')
            
            thumbnail.image_url = thumbnail_image_url
            thumbnail.save()

            if old_thumbnail_key:
                delete_s3_object.delay(old_thumbnail_key)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        if request.user.is_authenticated:
            save_view_model.delay(collection_id=instance.pk, user_id=request.user.pk)

        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='presigned-url-for-thumbnail')
    def presigned_url_for_thumbnail(self, request):
        file_name = request.data.get('fileName')
        file_type = request.data.get('fileType')

        if not file_name or not file_type:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={"error": "fileName and fileType are required."})

        s3_file_key = f"thumbnails/{uuid.uuid4()}_{file_name}"
        s3_client = get_boto3_client()

        try:
            presigned_url = s3_client.generate_presigned_url(
                'put_object',
                Params={'Bucket': settings.AWS_BUCKET_NAME,
                        'Key': s3_file_key,
                        'ContentType': file_type},
                ExpiresIn=600  # 10 minutes
            )
            image_url = f"{settings.AWS_CLOUDFRONT_URL}/{s3_file_key}"
            return Response({"presignedUrl": presigned_url, "imageUrl": image_url})
        except ClientError as e:
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR, data={"error": str(e)})

    @action(detail=True, methods=['post'], url_path='toggle-bookmark')
    def toggle_bookmark(self, request, pk=None):
        collection = self.get_object()
        user = request.user

        bookmark = Bookmark.objects.get(owner=user)

        if bookmark.collections.filter(pk=collection.pk).exists():
            bookmark.collections.remove(collection)

            return Response({"status": "removed"})

        else:
            bookmark.collections.add(collection)

            return Response({"status": "added"})

    @action(detail=True, methods=['post'], url_path='generate-share-link')
    def generate_share_link(self, request, pk=None):
        collection = self.get_object()

        expire_date = request.data.get("expireDate", 9999)

        if collection.is_expired:
            collection.share_uuid = uuid.uuid4()

        collection.expire_date = timezone.now() + timedelta(days=expire_date)
        collection.save()

        return Response({"share_link": f"http://localhost:8080/collections/{collection.share_uuid}"})

    @action(detail=False, methods=['get'], url_path='(?P<share_uuid>[0-9a-f-]{36})', permission_classes=[AllowAny])
    def get_collection_via_share_link(self, request, share_uuid, pk=None):
        try:
            collection = LinkCollection.objects.get(share_uuid=share_uuid)

            if collection.is_expired or str(collection.share_uuid) != share_uuid:
                return Response(status=status.HTTP_404_NOT_FOUND, data={"error": "링크가 만료되었거나 잘못된 링크입니다."})

            serializer = self.get_serializer(collection)
            return Response(serializer.data)

        except LinkCollection.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND, data={"error": "잘못된 링크입니다."})

    @action(detail=True, methods=['post'], url_path='toggle-like', permission_classes=[IsAuthenticated])
    def toggle_like(self, request, pk=None):
        user = request.user

        if not user.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED, data={"error": "로그인이 필요합니다."})

        collection = self.get_object()
        if not collection.is_public and collection.owner != request.user:
            return Response(status=status.HTTP_403_FORBIDDEN, data={"error": "비공개 링크 모음입니다."})

        if collection.owner == request.user:
            return Response(status=status.HTTP_403_FORBIDDEN, data={"error": "Self-like is forbidden."})

        try:
            qs = LinkCollectionLike.objects.filter(collection=collection, liker=request.user)
            if qs.exists():
                qs.delete()

                return Response({"message": "Like deleted."})
            else:
                LinkCollectionLike.objects.create(collection=collection, liker=request.user)

                return Response({"message": "Like created."})

        except Exception as e:
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR, data={"error": str(e)})

    @action(detail=False, methods=['get'], url_path='owned-or-all', permission_classes=[AllowAny])
    def get_owned_or_all_collections(self, request):
        user = request.user
        filter_word = request.GET.get('filter', 'likes')
        search_word = request.GET.get('search', None)

        liked_collection_pks = set()
        bookmarked_collection_pks = set()

        if user.is_authenticated:
            liked_collection_pks = set(
                LinkCollectionLike.objects.filter(liker=user).values_list('collection_id', flat=True)
            )
            bookmarked_collection_pks = set(
                user.bookmark.collections.values_list('id', flat=True)
            )

        base_qs = LinkCollection.objects.select_related('owner').prefetch_related('links')

        if not user.is_authenticated:
            qs = base_qs.filter(is_public=True)
        else:
            qs = base_qs.filter(Q(is_public=True) | Q(owner=user))

        if search_word is not None:
            qs = qs.filter(title__icontains=search_word)

        if filter_word == 'likes':
            qs = qs.annotate(total_likes=Count('likes')).order_by('-total_likes', '-pk')
        elif filter_word == 'views':
            qs = qs.annotate(view_counts=Count('views')).order_by('-view_counts', '-pk')
        else:
            qs = qs.annotate(view_counts=Count('views')).order_by('-pk')

        pagination = MainPageLinkCollectionPagination()
        page = pagination.paginate_queryset(qs, request)

        serializer_context = {
            'request': request,
            'liked_collection_pks': liked_collection_pks,
            'bookmarked_collection_pks': bookmarked_collection_pks,
            'filter_word': filter_word,
        }
        if page is not None:
            serializer = self.get_serializer(page, many=True, context=serializer_context)
            return pagination.get_paginated_response(serializer.data)

        serializer = self.get_serializer(qs, many=True, context=serializer_context)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='mine', permission_classes=[IsAuthenticated])
    def get_my_collections(self, request):
        user = request.user
        filter_word = request.GET.get('filter', 'latest')

        liked_collection_pks = set(
            LinkCollectionLike.objects.filter(liker=user).values_list('collection_id', flat=True)
        )
        bookmarked_collection_pks = set(
            user.bookmark.collections.values_list('id', flat=True)
        )

        qs = LinkCollection.objects.select_related('owner').prefetch_related('links').filter(owner=user)

        if filter_word == 'likes':
            qs = qs.annotate(total_likes=Count('likes')).order_by('-total_likes', '-pk')
        elif filter_word == 'views':
            qs = qs.annotate(view_counts=Count('views')).order_by('-view_counts', '-pk')
        else:
            qs = qs.order_by('-pk')

        pagination = MainPageLinkCollectionPagination()
        page = pagination.paginate_queryset(qs, request)

        serializer_context = {
            'request': request,
            'liked_collection_pks': liked_collection_pks,
            'bookmarked_collection_pks': bookmarked_collection_pks,
            'filter_word': filter_word,
        }
        if page is not None:
            serializer = self.get_serializer(page, many=True, context=serializer_context)
            return pagination.get_paginated_response(serializer.data)

        serializer = self.get_serializer(qs, many=True, context=serializer_context)
        return Response(serializer.data)

    @action(detail=True, methods=['delete'], url_path='share-link')
    def delete_share_link(self, request, pk=None):
        collection = self.get_object()

        collection.share_uuid = None
        collection.expire_date = None

        collection.save()

        return Response({"message": "공유 링크가 비활성화되었습니다."})
