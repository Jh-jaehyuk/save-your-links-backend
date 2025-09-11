from django.db import transaction
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response

from myapp.models import Link, LinkCollection
from myapp.permissions import IsOwnerOrReadOnly
from myapp.serializers import LinkSerializer


class LinkView(ModelViewSet):
    queryset = Link.objects.all()
    serializer_class = LinkSerializer
    permission_classes = [IsOwnerOrReadOnly]

    def create(self, request, *args, **kwargs):
        links = request.data.get('links', [])

        if not links:
            return Response(status=status.HTTP_400_BAD_REQUEST, data={"error": "links required."})

        if len(links) > 1:
            serializer = self.get_serializer(data=links, many=True)
        else:
            serializer = self.get_serializer(data=links[0])

        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(methods=['post'], detail=False, url_path='batch')
    def batch(self, request):
        added = request.data.get('added', [])
        updated = request.data.get('updated', [])
        deleted = request.data.get('deleted', [])

        try:
            with transaction.atomic():
                if added:
                    collection = LinkCollection.objects.get(pk=added[0]['collection'])
                    added_links = [Link(title=link['title'], url=link['url'], description=link['description'], collection=collection) for link in added]
                    Link.objects.bulk_create(added_links)

                if updated:
                    updated_links = [Link.objects.get(pk=link.id) for link in updated]
                    Link.objects.bulk_update(updated_links, ['title', 'content', 'description'])

                if deleted:
                    for link in deleted:
                        Link.objects.get(pk=link['id']).delete()

            return Response(status=status.HTTP_200_OK, data={"message": "batch 작업 성공"})

        except Exception as e:
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR, data={"error": str(e)})

