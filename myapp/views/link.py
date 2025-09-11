from rest_framework import status
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
