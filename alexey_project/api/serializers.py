from rest_framework import serializers

from core.models import TextDocument, Label, Annotation


class TextDocumentSerializer(serializers.ModelSerializer):

    class Meta:
        model = TextDocument
        fields = ('id', 'user', 'title', 'content', 'created_at')
        read_only_fields = ('user',)


class LabelSerializer(serializers.ModelSerializer):

    class Meta:
        model = Label
        fields = ('id', 'name', 'color')


class AnnotationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Annotation
        fields = ('id', 'document', 'label', 'start', 'end', 'text',
                  'created_at')
        read_only_fields = ('text',)
