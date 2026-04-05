from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import FinancialRecord, User


# ─────────────────────────── User Serializers ───────────────────────────


class UserSerializer(serializers.ModelSerializer):
    """Read serializer — used in list / detail responses."""

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name",
            "role", "is_active", "date_joined",
        ]
        read_only_fields = ["id", "date_joined"]


class UserCreateSerializer(serializers.ModelSerializer):
    """
    Write serializer — handles user creation with password hashing.
    Only admins should call this endpoint (enforced in the view).
    """

    password = serializers.CharField(
        write_only=True, required=True, validators=[validate_password]
    )
    password_confirm = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name",
            "password", "password_confirm", "role", "is_active",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password_confirm"):
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."}
            )
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """Partial update serializer — admins can change role / status."""

    class Meta:
        model = User
        fields = ["email", "first_name", "last_name", "role", "is_active"]


# ──────────────────────── Financial Record Serializers ────────────────────────


class FinancialRecordSerializer(serializers.ModelSerializer):
    """Read/write serializer for financial records."""

    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = FinancialRecord
        fields = [
            "id", "user", "amount", "entry_type", "category",
            "date", "description", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at"]

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value


# ──────────────────────── Dashboard Summary Serializers ────────────────────────


class DashboardSummarySerializer(serializers.Serializer):
    """Response shape for the dashboard summary endpoint."""

    total_income = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_expenses = serializers.DecimalField(max_digits=14, decimal_places=2)
    net_balance = serializers.DecimalField(max_digits=14, decimal_places=2)
    record_count = serializers.IntegerField()


class CategoryTotalSerializer(serializers.Serializer):
    category = serializers.CharField()
    total = serializers.DecimalField(max_digits=14, decimal_places=2)


class MonthlyTrendSerializer(serializers.Serializer):
    month = serializers.DateField(format="%Y-%m")
    income = serializers.DecimalField(max_digits=14, decimal_places=2)
    expenses = serializers.DecimalField(max_digits=14, decimal_places=2)