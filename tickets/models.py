from django.db import models
import uuid
from django.contrib.auth.models import AbstractUser
from django.conf import settings

ROLE_CHOICES = (
    ('TESTER', 'Tester'),
    ('DEVELOPER', 'Developer'),
    ('QA', 'QA'),
    ('ADMIN', 'Admin'),
)


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=150, unique=True)
    full_name = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='TESTER')

    def __str__(self):
        return self.username


# --- Ticket domain ---
SEVERITY_CHOICES = (
    ('HINT', 'Hint'),
    ('NORMAL', 'Normal'),
    ('SEVERE', 'Severe'),
    ('CRITICAL', 'Critical'),
)

TICKET_STATUS_CHOICES = (
    ('OPEN', 'Open'),
    ('IN_DEVELOPMENT', 'In Development'),
    ('UNDER_REVIEW', 'Under Review'),
    ('IN_REGRESSION', 'In Regression'),
    ('IN_MODIFICATION', 'In Modification'),
    ('CLOSED', 'Closed'),
    ('REOPENED', 'Reopened'),
)


class Ticket(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    software_name = models.CharField(max_length=255, blank=True)
    software_version = models.CharField(max_length=255, blank=True)
    discovered_at = models.DateTimeField()

    severity = models.CharField(max_length=16, choices=SEVERITY_CHOICES, default='NORMAL')
    module = models.CharField(max_length=255, blank=True)

    current_status = models.CharField(max_length=32, choices=TICKET_STATUS_CHOICES, default='OPEN', db_index=True)

    submitter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='submitted_tickets')
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name='assigned_tickets', null=True, blank=True)
    qa_reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name='qa_reviewed_tickets', null=True, blank=True)
    regressor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name='regressed_tickets', null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"[{self.current_status}] {self.title}"

    class Meta:
        indexes = [
            models.Index(fields=['current_status']),
            models.Index(fields=['assignee']),
            models.Index(fields=['submitter']),
        ]