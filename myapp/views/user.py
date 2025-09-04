import uuid

from botocore.exceptions import ClientError
from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Count
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from myapp.models import Bookmark, LinkCollectionLike, UserAvatar
from myapp.paginations import MainPageLinkCollectionPagination
from myapp.serializers import UserSerializer, UserinfoSerializer, LinkCollectionListSerializer
from myapp.tasks import delete_s3_object
from myapp.utils import get_boto3_client


class UserView(ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    @action(methods=['post'], detail=False, url_path='check-nickname')
    def check_nickname(self, request):
        nickname = request.data.get('nickname', None)
        if not nickname:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={"error": "Nickname is required."})

        is_taken = User.objects.filter(username=nickname).exclude(pk=request.user.pk).exists()
        if is_taken:
            return Response({"is_available": False, "message": "This nickname is already taken."})
        else:
            return Response({"is_available": True, "message": "This nickname is available."})

    @action(methods=['post'], detail=False, url_path='presigned-url-for-avatar')
    def presigned_url_for_avatar(self, request):
        file_name = request.data.get('fileName')
        file_type = request.data.get('fileType')

        if not file_name or not file_type:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={"error": "fileName and fileType are required."})

        s3_file_key = f"avatar/{uuid.uuid4()}_{file_name}"
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

    @action(methods=['get'], detail=False, url_path='bookmark')
    def get_bookmark(self, request):
        user = request.user

        if not user.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED, data={"error": "로그인이 필요합니다"})

        try:
            bookmark = Bookmark.objects.get(owner=user)
            qs = bookmark.collections.select_related('owner').prefetch_related('links').all()

            liked_collection_pks = set(
                LinkCollectionLike.objects.filter(liker=user).values_list('collection_id', flat=True)
            )
            bookmarked_collection_pks = set(qs.values_list('id', flat=True))

            filter_word = request.GET.get('filter', 'latest')
            if filter_word == 'likes':
                qs = qs.annotate(total_likes=Count('likes')).order_by('-total_likes', '-pk')
            elif filter_word == 'views':
                qs = qs.annotate(view_counts=Count('views')).order_by('-view_counts', '-pk')
            else: # latest
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
                serializer = LinkCollectionListSerializer(page, many=True, context=serializer_context)
                return pagination.get_paginated_response(serializer.data)

            serializer = LinkCollectionListSerializer(qs, many=True, context=serializer_context)
            return Response(serializer.data)

        except Bookmark.DoesNotExist:
            return Response({
                'count': 0,
                'next': None,
                'previous': None,
                'results': []
            })

    @action(detail=False, methods=['get', 'put'], url_path='me')
    def me(self, request):
        user = request.user

        if not user.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED, data={"error": "로그인이 필요합니다"})

        if request.method == "GET":
            serializer = UserinfoSerializer(user)
            return Response(serializer.data)

        # PUT Method
        try:
            with transaction.atomic():
                new_nickname = request.data.get('newNickname')
                new_avatar_url = request.data.get('newUserAvatarUrl')
                old_avatar_key = None

                if new_nickname and new_nickname != user.username:
                    if User.objects.filter(username=new_nickname).exclude(pk=user.pk).exists():
                        return Response(status=status.HTTP_400_BAD_REQUEST, data={"error": "이미 존재하는 닉네임입니다."})
                    user.username = new_nickname
                    user.save()

                if new_avatar_url:
                    avatar, created = UserAvatar.objects.get_or_create(user=user)
                    if not created and avatar.image_url:
                        # Extract key from CloudFront URL
                        old_avatar_key = avatar.image_url.replace(settings.AWS_CLOUDFRONT_URL + '/', '')
                    
                    avatar.image_url = new_avatar_url
                    avatar.save()

                # After transaction is successful, dispatch cleanup task
                if old_avatar_key:
                    delete_s3_object.delay(old_avatar_key)

            # Return the updated user info
            serializer = UserinfoSerializer(user)
            return Response(serializer.data)

        except Exception as e:
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR, data={"error": str(e)})
