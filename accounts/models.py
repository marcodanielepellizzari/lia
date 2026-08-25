from django.contrib.auth.models import AbstractUser
from django.db import models


class Role(models.TextChoices):
    """
    The 4 roles from the "Security management - Roles" slide.
    'Unregistered' is not a role stored in the DB: it simply corresponds
    to request.user.is_authenticated == False (only sees public data).
    """
    ADMIN = "admin", "Admin"
    REVIEWER = "reviewer", "Reviewer"
    REGISTERED = "registered", "Registered user"


class Team(models.Model):
    """
    Group of users who can share private datasets with each other
    (slide 3: "ability to share with other users").
    """
    name = models.CharField(max_length=120, unique=True)
    members = models.ManyToManyField("accounts.User", related_name="teams", blank=True)

    def __str__(self):
        return self.name


class User(AbstractUser):
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.REGISTERED)

    # --- role helpers, used everywhere instead of scattered string checks ---
    @property
    def is_admin_role(self):
        return self.role == Role.ADMIN or self.is_superuser

    @property
    def is_reviewer(self):
        return self.role == Role.REVIEWER or self.is_admin_role

    @property
    def is_registered(self):
        # any logged-in user is at least "Registered"
        return self.is_authenticated

    def __str__(self):
        return self.username
