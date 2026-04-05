from django.shortcuts import render

# Create your views here.
from django.db.models import DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce, TruncMonth
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import FinancialRecord, User
from .permissions import IsActiveUser, IsAdmin, IsAnalystOrAbove, RecordPermission
from .serializers import (
    CategoryTotalSerializer,
    DashboardSummarySerializer,
    FinancialRecordSerializer,
    MonthlyTrendSerializer,
    UserCreateSerializer,
    UserSerializer,
    UserUpdateSerializer,
)


# ═══════════════════════════ USER MANAGEMENT ═══════════════════════════


class UserListCreateView(generics.ListCreateAPIView):
    """
    GET  → List all users          (Admin only)
    POST → Create a new user       (Admin only)
    """

    queryset = User.objects.all()
    permission_classes = [IsAuthenticated, IsActiveUser, IsAdmin]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return UserCreateSerializer
        return UserSerializer


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    → Retrieve user details   (Admin only)
    PATCH  → Update user / role      (Admin only)
    DELETE → Deactivate user         (Admin only — soft-delete)
    """

    queryset = User.objects.all()
    permission_classes = [IsAuthenticated, IsActiveUser, IsAdmin]
    lookup_field = "pk"

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return UserUpdateSerializer
        return UserSerializer

    def destroy(self, request, *args, **kwargs):
        """Soft-delete: deactivate instead of removing from the database."""
        user = self.get_object()
        user.is_active = False
        user.save(update_fields=["is_active"])
        return Response(
            {"detail": f"User '{user.username}' has been deactivated."},
            status=status.HTTP_200_OK,
        )


class CurrentUserView(APIView):
    """Return the profile of the currently authenticated user."""

    permission_classes = [IsAuthenticated, IsActiveUser]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
    

# ═══════════════════════════ FINANCIAL RECORDS ═══════════════════════════


class FinancialRecordListCreateView(generics.ListCreateAPIView):
    """
    GET  → List records with filtering, search, ordering
    POST → Create a record (Admin only — enforced by RecordPermission)
    """

    serializer_class = FinancialRecordSerializer
    permission_classes = [IsAuthenticated, IsActiveUser, RecordPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        "entry_type": ["exact"],
        "category": ["exact"],
        "date": ["exact", "gte", "lte"],
        "amount": ["gte", "lte"],
    }
    search_fields = ["description", "category"]
    ordering_fields = ["date", "amount", "created_at"]
    ordering = ["-date"]

    def get_queryset(self):
        return FinancialRecord.objects.select_related("user")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class FinancialRecordDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    → Retrieve a single record
    PATCH  → Update a record  (Admin only)
    DELETE → Delete a record  (Admin only)
    """

    serializer_class = FinancialRecordSerializer
    permission_classes = [IsAuthenticated, IsActiveUser, RecordPermission]
    lookup_field = "pk"

    def get_queryset(self):
        return FinancialRecord.objects.select_related("user")
    
# ═══════════════════════════ DASHBOARD ANALYTICS ═══════════════════════════

ZERO = Value(0, output_field=DecimalField())


class DashboardSummaryView(APIView):
    """
    GET → Returns total income, total expenses, net balance, and record count.
    Accessible by Analyst and Admin.
    Supports optional query params: ?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD
    """

    permission_classes = [IsAuthenticated, IsActiveUser, IsAnalystOrAbove]

    def get(self, request):
        qs = FinancialRecord.objects.all()
        qs = self._apply_date_filters(request, qs)

        totals = qs.aggregate(
            total_income=Coalesce(
                Sum("amount", filter=Q(entry_type="income")), ZERO
            ),
            total_expenses=Coalesce(
                Sum("amount", filter=Q(entry_type="expense")), ZERO
            ),
        )

        totals["net_balance"] = totals["total_income"] - totals["total_expenses"]
        totals["record_count"] = qs.count()

        serializer = DashboardSummarySerializer(totals)
        return Response(serializer.data)

    @staticmethod
    def _apply_date_filters(request, qs):
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)
        return qs


class CategoryBreakdownView(APIView):
    """
    GET → Category-wise totals, optionally filtered by entry_type and date range.
    Query params: ?entry_type=income|expense&date_from=...&date_to=...
    """

    permission_classes = [IsAuthenticated, IsActiveUser, IsAnalystOrAbove]

    def get(self, request):
        qs = FinancialRecord.objects.all()

        entry_type = request.query_params.get("entry_type")
        if entry_type in ("income", "expense"):
            qs = qs.filter(entry_type=entry_type)

        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)

        breakdown = (
            qs.values("category")
            .annotate(total=Coalesce(Sum("amount"), ZERO))
            .order_by("-total")
        )

        serializer = CategoryTotalSerializer(breakdown, many=True)
        return Response(serializer.data)


class MonthlyTrendView(APIView):
    """
    GET → Monthly income vs expense trend for the last 12 months (or custom range).
    """

    permission_classes = [IsAuthenticated, IsActiveUser, IsAnalystOrAbove]

    def get(self, request):
        qs = FinancialRecord.objects.all()

        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)

        trends = (
            qs.annotate(month=TruncMonth("date"))
            .values("month")
            .annotate(
                income=Coalesce(
                    Sum("amount", filter=Q(entry_type="income")), ZERO
                ),
                expenses=Coalesce(
                    Sum("amount", filter=Q(entry_type="expense")), ZERO
                ),
            )
            .order_by("month")
        )

        serializer = MonthlyTrendSerializer(trends, many=True)
        return Response(serializer.data)


class RecentActivityView(generics.ListAPIView):
    """
    GET → Last N records (default 10). Useful for a dashboard feed.
    Query param: ?limit=10
    """

    serializer_class = FinancialRecordSerializer
    permission_classes = [IsAuthenticated, IsActiveUser, IsAnalystOrAbove]

    def get_queryset(self):
        limit = self.request.query_params.get("limit", 10)
        try:
            limit = min(int(limit), 50)
        except (ValueError, TypeError):
            limit = 10
        return FinancialRecord.objects.select_related("user")[:limit]