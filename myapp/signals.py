from django.contrib.auth.models import User
from django.db.models import F
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from myapp.models import Bookmark, UserAvatar, LinkCollection, LinkCollectionThumbnail, LinkCollectionLike, \
    LinkCollectionViewModel


@receiver(post_save, sender=User)
def create_user_bookmark(sender, instance, created, **kwargs):
    if created:
        Bookmark.objects.create(owner=instance)

@receiver(post_save, sender=User)
def create_user_avatar(sender, instance, created, **kwargs):
    if created:
        UserAvatar.objects.create(user=instance)

@receiver(post_save, sender=LinkCollection)
def create_link_collection_thumbnail(sender, instance, created, **kwargs):
    if created:
        LinkCollectionThumbnail.objects.create(collection=instance)

@receiver(post_save, sender=LinkCollectionLike)
def increment_like_count(sender, instance, created, **kwargs):
    if created:
        instance.collection.likes_count = F('likes_count') + 1
        instance.collection.save(update_fields=['likes_count'])

@receiver(post_delete, sender=LinkCollectionLike)
def decrement_like_count(sender, instance, **kwargs):
    instance.collection.likes_count = F('likes_count') - 1
    instance.collection.save(update_fields=['likes_count'])

@receiver(post_save, sender=LinkCollectionViewModel)
def increment_view_count(sender, instance, created, **kwargs):
    if created:
        instance.collection.views_count = F('views_count') + 1
        instance.collection.save(update_fields=['views_count'])
