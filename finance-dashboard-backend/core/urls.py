from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    # ──── Authentication helper ────
    path("me/", views.CurrentUserView.as_view(), name="current-user"),

    # ──── User management (Admin only) ────
    path("users/", views.UserListCreateView.as_view(), name="user-list"),
    path("users/<uuid:pk>/", views.UserDetailView.as_view(), name="user-detail"),

    # ──── Financial records ────
    path(
        "records/",
        views.FinancialRecordListCreateView.as_view(),
        name="record-list",
    ),
    path(
        "records/<uuid:pk>/",
        views.FinancialRecordDetailView.as_view(),
        name="record-detail",
    ),

    # ──── Dashboard / Analytics ────
    path("dashboard/summary/", views.DashboardSummaryView.as_view(), name="dashboard-summary"),
    path("dashboard/categories/", views.CategoryBreakdownView.as_view(), name="category-breakdown"),
    path("dashboard/trends/", views.MonthlyTrendView.as_view(), name="monthly-trends"),
    path("dashboard/recent/", views.RecentActivityView.as_view(), name="recent-activity"),
]