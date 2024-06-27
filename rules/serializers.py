# serializers.py
from rest_framework import serializers
from .models import Node, Edge

class NodeSerializer(serializers.ModelSerializer):
    position = serializers.SerializerMethodField()

    class Meta:
        model = Node
        fields = ['id', 'type', 'label', 'description', 'position']

    def get_position(self, obj):
        return {'x': obj.position_x, 'y': obj.position_y}

class EdgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Edge
        fields = ['id', 'source', 'target', 'type', 'label']
