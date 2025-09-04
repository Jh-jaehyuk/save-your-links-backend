from rest_framework import permissions

from myapp.models import Bookmark, LinkCollection


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.

        if isinstance(obj, Bookmark):
            return obj.owner == request.user

        if request.method in permissions.SAFE_METHODS:
            if isinstance(obj, LinkCollection):
                if obj.is_public:
                    return True
                else:
                    return obj.owner == request.user

            return True

        # Write permissions are only allowed to the owner of the snippet.
        if hasattr(obj, 'collection'):
            return obj.collection.owner == request.user

        return obj.owner == request.user
