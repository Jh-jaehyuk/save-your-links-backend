from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from myapp.models import Bookmark, UserAvatar, LinkCollection, LinkCollectionThumbnail


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
