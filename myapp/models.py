from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


# Create your models here.
class LinkCollection(models.Model):
    title = models.CharField(max_length=50, blank=False, null=False, verbose_name="링크 모음 제목")
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="collections", verbose_name="링크 모음 소유자")
    description = models.TextField(blank=True, null=False, verbose_name="링크 모음 설명")
    is_public = models.BooleanField(default=False, verbose_name="링크 모음 공개 여부")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    share_uuid = models.UUIDField(null=True, blank=False, verbose_name="링크 모음 공유 링크 UUID")
    expire_date = models.DateTimeField(null=True, blank=False, verbose_name="링크 모음 공유 링크 만료 기간")

    def __str__(self):
        return f"LinkCollection #{self.pk} ({"public" if self.is_public else "private"})\nTitle: {self.title}, Number of links: {len(self.links.all())}"

    @property
    def is_expired(self):
        return self.expire_date is None or self.expire_date < timezone.now()

    class Meta:
        db_table = "link_collections"
        verbose_name = "링크 모음"
        verbose_name_plural = "링크 모음 목록"

class Link(models.Model):
    title = models.CharField(max_length=50, blank=False, null=False, verbose_name="링크 제목")
    url = models.URLField(max_length=256, blank=False, null=False, verbose_name="링크 URL")
    description = models.TextField(blank=True, null=False, verbose_name="링크 설명")
    collection = models.ForeignKey(LinkCollection, on_delete=models.CASCADE, related_name="links", verbose_name="링크가 포함된 컬렉션")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Link #{self.pk}\nTitle: {self.title}, URL: {self.url}\nDescription: {self.description}"

    class Meta:
        db_table = "links"
        verbose_name = "링크"
        verbose_name_plural = "링크 목록"

class Bookmark(models.Model):
    owner = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="즐겨찾기 소유자")
    collections = models.ManyToManyField(LinkCollection, related_name="bookmarks", verbose_name="포함된 링크 모음들")

    def __str__(self):
        return f"Bookmark #{self.pk} (Owner: {self.owner.username})"

    class Meta:
        db_table = "bookmarks"
        verbose_name = "즐겨찾기"
        verbose_name_plural = "즐겨찾기 목록"

class LinkCollectionLike(models.Model):
    collection = models.ForeignKey(LinkCollection, on_delete=models.CASCADE, related_name="likes", verbose_name="좋아요 누른 링크 모음")
    liker = models.ForeignKey(User, on_delete=models.CASCADE, related_name="likes", verbose_name="좋아요 누른 사용자")

    def __str__(self):
        return f"LinkCollectionLike #{self.pk} (Collection: {self.collection.pk}, Liker: {self.liker.username})"

    class Meta:
        db_table = "link_collection_likes"
        verbose_name = "좋아요"
        verbose_name_plural = "좋아요 목록"

class LinkCollectionViewModel(models.Model):
    collection = models.ForeignKey(LinkCollection, on_delete=models.CASCADE, related_name="views", verbose_name="조회한 링크 모음")
    viewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="views", verbose_name="조회한 사용자")

    def __str__(self):
        return f"LinkCollectionViewModel #{self.pk} (Collection: {self.collection.pk}, Viewer: {self.viewer.username})"

    class Meta:
        db_table = "link_collection_view"
        constraints = [
            # 이전 버전의 unique_together를 대체
            models.UniqueConstraint(
                fields=['collection', 'viewer'],
                name='unique_collection_viewer'
            )
        ]
        verbose_name = "조회"
        verbose_name_plural = "조회 목록"

class UserAvatar(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="avatar", verbose_name="아바타 소유자")
    image_url = models.URLField(max_length=256, null=True, blank=False, verbose_name="아바타 CloudFront URL")

    def __str__(self):
        return f"Avatar #{self.pk} (User: {self.user.username}, URL: {self.image_url})"

    class Meta:
        db_table = "user_avatars"
        verbose_name = "사용자 아바타"
        verbose_name_plural = "사용자 아바타 목록"

class LinkCollectionThumbnail(models.Model):
    collection = models.OneToOneField(LinkCollection, on_delete=models.CASCADE, related_name='thumbnail', verbose_name="썸네일 컬렉션")
    image_url = models.URLField(max_length=256, null=True, blank=False, verbose_name="썸네일 URL")

    def __str__(self):
        return f"Thumbnail #{self.pk} (Collection: {self.collection.pk}, URL: {self.image_url})"

    class Meta:
        db_table = "link_collection_thumbnail"
        verbose_name = "링크 모음 썸네일"
        verbose_name_plural = "링크 모음 썸네일 목록"
