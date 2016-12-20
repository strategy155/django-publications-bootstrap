from rest_framework import serializers
from django.db import DatabaseError
from publications.models import Publication, Type


class TypeSerializer(serializers.ModelSerializer):

    class Meta:
        model = Type
        fields = ['type']


class PublicationSerializer(serializers.Serializer):

    class Meta:
        model = Publication
        fields = [
                'type',
                'doi',
                'authors',
                'year',
                'title',
                'journal',
                'volume',
                'number',
                'pages',
                'url',
                'isbn',
                ]

    def create(self, validated_data):
        """
        Create and return publication object.
        Will raise django.db.IntegrityError if validated_data
        not unique in doi and isbn
        """
        return Publication.objects.create(**validated_data)
