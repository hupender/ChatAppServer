from django.contrib.auth.models import BaseUserManager
from django.db import models
from common.models import BaseModel
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.utils.translation import gettext_lazy as _
from .helpers import clean_mobile_number, validate_language
from common.helpers import generate_random_string

class PersonManager(BaseUserManager):
    # def _create_user(self, username, email, password, **extra_fields):
    #     """
    #     Create and save a user with the given username, email, and password.
    #     """
    def _create_user(self, username, password, **extra_fields):
        """
        Create and save a user with the given username, email, and password.
        """
        if not username:
            raise ValueError("The given username must be set")
        username = self.model.normalize_username(username)
        user = self.model(username=username, **extra_fields)
        
        user.set_password(password)
        user.save(using=self._db)

        return user

    def _get_unique_random_id(self,field):
        """
        generates unique username/string of size 8 as of now
        """
        while True:
            res = generate_random_string(length=8)
            if field == "username":
                if not Users.objects.filter(username=res).exists():
                    return res
            if field == "account_number":
                if not Users.objects.filter(account_number=res).exists():
                    return res


    def create_user(self, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        username = self._get_unique_random_id("username")
        extra_fields["account_number"] = self._get_unique_random_id("account_number")
        return self._create_user(username, password, **extra_fields)
    
    
    def create_staff(self, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", False)
        username = self._get_unique_random_id("username")
        extra_fields["account_number"] = self._get_unique_random_id("account_number")
        return self._create_user(username, password, **extra_fields)

    
    def create_superuser(self, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_root", True)
        username = self._get_unique_random_id("username")
        extra_fields["account_number"] = self._get_unique_random_id("account_number")
        return self._create_user(username, password, **extra_fields)



class Users(BaseModel, AbstractUser):
    username_validator = UnicodeUsernameValidator()

    username = models.CharField(
        _("username"),
        max_length=150,
        unique=True,
        help_text=_(
            "Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only."
        ),
        validators=[username_validator],
        error_messages={
            "unique": _("A user with that username already exists."),
        },
    )
    first_name = models.CharField(_("first name"), max_length=150, blank=True)
    last_name = models.CharField(_("last name"), max_length=150, blank=True)
    email = models.EmailField(_("email address"), blank=True, unique=True)
    mobile_number = models.CharField(_("mobile number"), blank=True, max_length=15, validators=[clean_mobile_number], unique=True)
    is_staff = models.BooleanField(
        _("staff status"),
        default=False,
        help_text=_("Designates whether the user can log into this admin site."),
    )
    is_active = models.BooleanField(
        _("active"),
        default=True,
        help_text=_(
            "Designates whether this user should be treated as active. "
            "Unselect this instead of deleting accounts."
        ),
    )
    is_root = models.BooleanField(
        _("Flag Root"), default=False, help_text=_("Designates whether this user is root or not.")
    )
    email_verified = models.BooleanField(_("email verified"), default=True, help_text=_("Designates wheather email is verified or not"))
    mobile_verified = models.BooleanField(_("mobile verified"), default=True, help_text=_("Designates wheather mobile is verified or not"))
    language = models.CharField(_("language"), default="en", validators=[validate_language], max_length=20)
    account_number = models.CharField(_("account number"), unique=True, max_length=20, blank=True)


    objects = PersonManager()

    EMAIL_FIELD = "email"
    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    @classmethod
    def get_full_name(cls, obj):
        return obj.first_name + " " + obj.last_name
