from django.db import models

# Create your models here.

import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom user with role-based access.
    Roles are stored directly on the user to keep the model simple.
    """

    class Role(models.TextChoices):
        VIEWER = "viewer", "Viewer"
        ANALYST = "analyst", "Analyst"
        ADMIN = "admin", "Admin"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.VIEWER,
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-date_joined"]

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def is_analyst(self):
        return self.role == self.Role.ANALYST

    @property
    def is_viewer(self):
        return self.role == self.Role.VIEWER
    


class FinancialRecord(models.Model):
    """A single financial entry — income or expense."""

    class EntryType(models.TextChoices):
        INCOME = "income", "Income"
        EXPENSE = "expense", "Expense"

    CATEGORY_CHOICES = [
        ("salary", "Salary"),
        ("freelance", "Freelance"),
        ("investment", "Investment"),
        ("food", "Food & Dining"),
        ("rent", "Rent / Housing"),
        ("shopping", "Shopping"),
        ("utilities", "Utilities"),
        ("transport", "Transport"),
        ("entertainment", "Entertainment"),
        ("healthcare", "Healthcare"),
        ("education", "Education"),
        ("other", "Other"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="financial_records",
        help_text="The user who created this record.",
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    entry_type = models.CharField(max_length=7, choices=EntryType.choices)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    date = models.DateField()
    description = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "-created_at"]
        indexes = [
            models.Index(fields=["entry_type"]),
            models.Index(fields=["category"]),
            models.Index(fields=["date"]),
            models.Index(fields=["user", "date"]),
        ]

    def __str__(self):
        return f"{self.get_entry_type_display()} — {self.amount} ({self.category})"