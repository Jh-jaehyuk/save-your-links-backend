from rest_framework import serializers

from myapp.models import Link


class LinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Link
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')
