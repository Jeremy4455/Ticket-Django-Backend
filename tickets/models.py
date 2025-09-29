from django.db import models
import uuid
from django.contrib.auth.models import AbstractUser

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