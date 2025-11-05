from __future__ import annotations
from rest_framework import serializers
from .models import CrossItem, ChangeSaleItem, AccessoryCategory, Accessory


class SimpleItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CrossItem  # може підмінятись у в'ю
        fields = ("id", "title", "short_note")


class ItemDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = CrossItem  # може підмінятись у в'ю
        fields = ("id", "title", "instruction_text")


class AccessoryCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessoryCategory
        fields = ("id", "name")


class AccessoryCategoryTextSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessoryCategory
        fields = ("id", "name", "instruction_text")


class AccessoryListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Accessory
        fields = ("id", "title", "short_note")


class AccessoryDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Accessory
        fields = ("id", "title", "instruction_text")


class ChangeSearchResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChangeSaleItem
        fields = ("id", "title", "instruction_text")
