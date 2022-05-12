from rest_framework import serializers
from .models import OURMODEL




class OURMODELSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = OURMODEL
        fields = ('field1', 'field2')