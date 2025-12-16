from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser
from django.utils import timezone
from django.db.models import signals
from django.dispatch import receiver
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import make_password, check_password

import uuid


class MyUserManager(BaseUserManager):
    def create_user(self, email : str, username : str, password=None):

        """
        Creates and saves a User with the given email, username and password.
        """

        if not email:
            raise ValueError("Users must have an email address")

        user = self.model(
            email=self.normalize_email(email),
            username=username,
        )

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None):

        """
        Creates and saves a superuser with the given email, username and password.
        """

        user = self.create_user(
            email,
            password=password,
            username=username,
        )

        user.is_admin = True
        user.is_staff_member = True
        user.is_active = True
        user.save(using=self._db)
        return user



class User(AbstractBaseUser):
    email = models.EmailField(
        verbose_name="email address",
        max_length=255,
        unique=True,
    )
    
    username = models.CharField(max_length=100)
    is_active = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)
    is_staff_member = models.BooleanField(default=False)
    user_profile_image = models.ImageField(upload_to="User Profiles", null=True, blank=True, default=None)
    verification_token = models.CharField(blank=True,null=True,unique=True,max_length=60)
    verification_token_expiry = models.DateTimeField(blank=True,null=True)
    otp = models.CharField(blank=True,null=True,unique=True,max_length=4)
    otp_expiry = models.DateTimeField(blank=True,null=True)
    is_two_factor_authentication_enabled = models.BooleanField(default=False)
    two_factor_pin = models.CharField(max_length=255, blank=True, null=True)


    objects = MyUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    
    def set_two_factor_pin(self, raw_pin):

        """
        Sets The Hashed Two Factor Authentication PIN
        """

        self.two_factor_pin = make_password(raw_pin)

    
    def verify_two_factor_pin(self, raw_pin):

        """
        Verify The Hashed Two Factor PIN. Inputs A Raw PIN To Match
        """

        return check_password(raw_pin, self.two_factor_pin)


    def __str__(self):
        return self.email

    def has_perm(self, perm, obj=None):
        "Does the user have a specific permission?"
        # Simplest possible answer: Yes, always
        return True

    def has_module_perms(self, app_label):
        "Does the user have permissions to view the app `app_label`?"
        # Simplest possible answer: Yes, always
        return True

    @property
    def is_staff(self):
        "Is the user a member of staff?"
        # Simplest possible answer: All admins are staff
        return self.is_admin or self.is_staff_member




class LoginAttempt(models.Model):
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    ip_address = models.GenericIPAddressField()
    timestamp = models.DateTimeField(default=timezone.now)
    success = models.BooleanField(default=False)




class OTPVerifyAttempt(models.Model):
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    ip_address = models.GenericIPAddressField()
    timestamp = models.DateTimeField(default=timezone.now)
    success = models.BooleanField(default=False)

