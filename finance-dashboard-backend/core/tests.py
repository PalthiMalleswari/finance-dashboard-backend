from django.test import TestCase

# Create your tests here.
"""
Test suite for the Finance Dashboard API.

Covers:
  - User management (CRUD + role enforcement)
  - Financial records (CRUD + filtering + validation)
  - Dashboard analytics (access control + correctness)
  - Error handling (invalid input → proper error shape)

Run:
    python manage.py test core -v 2
"""

from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from .models import FinancialRecord, User


class _BaseTestCase(TestCase):
    """Shared setup: creates one user per role and an API client."""

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username="admin", password="pass1234", role=User.Role.ADMIN,
        )
        self.analyst = User.objects.create_user(
            username="analyst", password="pass1234", role=User.Role.ANALYST,
        )
        self.viewer = User.objects.create_user(
            username="viewer", password="pass1234", role=User.Role.VIEWER,
        )

    def _login(self, user):
        self.client.force_authenticate(user=user)


# ═══════════════════════════════════════════════════════════════════════════
# USER MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════


class UserEndpointTests(_BaseTestCase):

    def test_admin_can_list_users(self):
        self._login(self.admin)
        resp = self.client.get(reverse("core:user-list"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_analyst_cannot_list_users(self):
        self._login(self.analyst)
        resp = self.client.get(reverse("core:user-list"))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_viewer_cannot_list_users(self):
        self._login(self.viewer)
        resp = self.client.get(reverse("core:user-list"))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_cannot_list_users(self):
        resp = self.client.get(reverse("core:user-list"))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_create_user(self):
        self._login(self.admin)
        resp = self.client.post(
            reverse("core:user-list"),
            {
                "username": "new_user",
                "password": "Strong!Pass99",
                "password_confirm": "Strong!Pass99",
                "role": "viewer",
            },
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username="new_user").exists())

    def test_create_user_password_mismatch(self):
        self._login(self.admin)
        resp = self.client.post(
            reverse("core:user-list"),
            {
                "username": "bad_user",
                "password": "Strong!Pass99",
                "password_confirm": "Wrong!Pass99",
                "role": "viewer",
            },
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_can_deactivate_user(self):
        self._login(self.admin)
        resp = self.client.delete(
            reverse("core:user-detail", kwargs={"pk": self.viewer.pk})
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.viewer.refresh_from_db()
        self.assertFalse(self.viewer.is_active)

    def test_admin_can_change_role(self):
        self._login(self.admin)
        resp = self.client.patch(
            reverse("core:user-detail", kwargs={"pk": self.viewer.pk}),
            {"role": "analyst"},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.viewer.refresh_from_db()
        self.assertEqual(self.viewer.role, User.Role.ANALYST)

    def test_current_user_endpoint(self):
        self._login(self.analyst)
        resp = self.client.get(reverse("core:current-user"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["username"], "analyst")


# ═══════════════════════════════════════════════════════════════════════════
# FINANCIAL RECORDS
# ═══════════════════════════════════════════════════════════════════════════


class RecordEndpointTests(_BaseTestCase):

    def setUp(self):
        super().setUp()
        self.record = FinancialRecord.objects.create(
            user=self.admin,
            amount=Decimal("500.00"),
            entry_type="expense",
            category="food",
            date=date.today(),
            description="Grocery shopping",
        )

    def test_all_roles_can_list_records(self):
        for user in [self.admin, self.analyst, self.viewer]:
            self._login(user)
            resp = self.client.get(reverse("core:record-list"))
            self.assertEqual(resp.status_code, status.HTTP_200_OK, msg=user.role)

    def test_admin_can_create_record(self):
        self._login(self.admin)
        resp = self.client.post(
            reverse("core:record-list"),
            {
                "amount": "3000.00",
                "entry_type": "income",
                "category": "salary",
                "date": "2025-03-01",
            },
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_viewer_cannot_create_record(self):
        self._login(self.viewer)
        resp = self.client.post(
            reverse("core:record-list"),
            {
                "amount": "100.00",
                "entry_type": "income",
                "category": "salary",
                "date": "2025-01-15",
            },
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_analyst_cannot_create_record(self):
        self._login(self.analyst)
        resp = self.client.post(
            reverse("core:record-list"),
            {
                "amount": "100.00",
                "entry_type": "income",
                "category": "salary",
                "date": "2025-01-15",
            },
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_update_record(self):
        self._login(self.admin)
        resp = self.client.patch(
            reverse("core:record-detail", kwargs={"pk": self.record.pk}),
            {"amount": "750.00"},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.record.refresh_from_db()
        self.assertEqual(self.record.amount, Decimal("750.00"))

    def test_admin_can_delete_record(self):
        self._login(self.admin)
        resp = self.client.delete(
            reverse("core:record-detail", kwargs={"pk": self.record.pk})
        )
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(FinancialRecord.objects.filter(pk=self.record.pk).exists())

    def test_viewer_cannot_delete_record(self):
        self._login(self.viewer)
        resp = self.client.delete(
            reverse("core:record-detail", kwargs={"pk": self.record.pk})
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_filter_by_entry_type(self):
        self._login(self.admin)
        resp = self.client.get(reverse("core:record-list"), {"entry_type": "expense"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        for item in resp.data["results"]:
            self.assertEqual(item["entry_type"], "expense")

    def test_filter_by_date_range(self):
        self._login(self.admin)
        resp = self.client.get(
            reverse("core:record-list"),
            {"date__gte": str(date.today()), "date__lte": str(date.today())},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(resp.data["results"]), 1)

    def test_negative_amount_rejected(self):
        self._login(self.admin)
        resp = self.client.post(
            reverse("core:record-list"),
            {
                "amount": "-50.00",
                "entry_type": "expense",
                "category": "food",
                "date": "2025-01-01",
            },
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_zero_amount_rejected(self):
        self._login(self.admin)
        resp = self.client.post(
            reverse("core:record-list"),
            {
                "amount": "0.00",
                "entry_type": "expense",
                "category": "food",
                "date": "2025-01-01",
            },
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_entry_type_rejected(self):
        self._login(self.admin)
        resp = self.client.post(
            reverse("core:record-list"),
            {
                "amount": "100.00",
                "entry_type": "refund",
                "category": "food",
                "date": "2025-01-01",
            },
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


# ═══════════════════════════════════════════════════════════════════════════
# DASHBOARD ANALYTICS
# ═══════════════════════════════════════════════════════════════════════════


class DashboardTests(_BaseTestCase):

    def setUp(self):
        super().setUp()
        FinancialRecord.objects.create(
            user=self.admin, amount=Decimal("5000.00"),
            entry_type="income", category="salary", date=date.today(),
        )
        FinancialRecord.objects.create(
            user=self.admin, amount=Decimal("1200.00"),
            entry_type="expense", category="rent", date=date.today(),
        )
        FinancialRecord.objects.create(
            user=self.admin, amount=Decimal("300.00"),
            entry_type="expense", category="food", date=date.today(),
        )

    # ── Access control ──

    def test_analyst_can_view_summary(self):
        self._login(self.analyst)
        resp = self.client.get(reverse("core:dashboard-summary"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_admin_can_view_summary(self):
        self._login(self.admin)
        resp = self.client.get(reverse("core:dashboard-summary"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_viewer_cannot_view_summary(self):
        self._login(self.viewer)
        resp = self.client.get(reverse("core:dashboard-summary"))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_viewer_cannot_view_categories(self):
        self._login(self.viewer)
        resp = self.client.get(reverse("core:category-breakdown"))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_viewer_cannot_view_trends(self):
        self._login(self.viewer)
        resp = self.client.get(reverse("core:monthly-trends"))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    # ── Correctness ──

    def test_summary_totals_are_correct(self):
        self._login(self.admin)
        resp = self.client.get(reverse("core:dashboard-summary"))
        self.assertEqual(Decimal(resp.data["total_income"]), Decimal("5000.00"))
        self.assertEqual(Decimal(resp.data["total_expenses"]), Decimal("1500.00"))
        self.assertEqual(Decimal(resp.data["net_balance"]), Decimal("3500.00"))
        self.assertEqual(resp.data["record_count"], 3)

    def test_category_breakdown(self):
        self._login(self.admin)
        resp = self.client.get(reverse("core:category-breakdown"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        categories = {item["category"] for item in resp.data}
        self.assertIn("rent", categories)
        self.assertIn("food", categories)

    def test_category_filter_by_type(self):
        self._login(self.admin)
        resp = self.client.get(
            reverse("core:category-breakdown"), {"entry_type": "expense"}
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        categories = {item["category"] for item in resp.data}
        self.assertNotIn("salary", categories)

    def test_monthly_trends(self):
        self._login(self.admin)
        resp = self.client.get(reverse("core:monthly-trends"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(resp.data), 1)

    def test_recent_activity(self):
        self._login(self.analyst)
        resp = self.client.get(reverse("core:recent-activity"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_recent_activity_limit(self):
        self._login(self.admin)
        resp = self.client.get(reverse("core:recent-activity"), {"limit": "2"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(resp.data["results"]), 2)


# ═══════════════════════════════════════════════════════════════════════════
# ERROR RESPONSE SHAPE
# ═══════════════════════════════════════════════════════════════════════════


class ErrorResponseTests(_BaseTestCase):

    def test_403_has_consistent_error_shape(self):
        self._login(self.viewer)
        resp = self.client.get(reverse("core:user-list"))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(resp.data["error"])
        self.assertEqual(resp.data["status_code"], 403)
        self.assertIn("message", resp.data)

    def test_400_has_consistent_error_shape(self):
        self._login(self.admin)
        resp = self.client.post(reverse("core:record-list"), {})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(resp.data["error"])
        self.assertEqual(resp.data["status_code"], 400)

    def test_404_for_nonexistent_record(self):
        self._login(self.admin)
        import uuid
        fake_id = uuid.uuid4()
        resp = self.client.get(
            reverse("core:record-detail", kwargs={"pk": fake_id})
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(resp.data["error"])


# ═══════════════════════════════════════════════════════════════════════════
# INACTIVE USER
# ═══════════════════════════════════════════════════════════════════════════


class InactiveUserTests(_BaseTestCase):

    def test_inactive_user_is_rejected(self):
        self.viewer.is_active = False
        self.viewer.save()
        self._login(self.viewer)
        resp = self.client.get(reverse("core:record-list"))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)