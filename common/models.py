from django.db import models
from uuid import uuid4

# Create your models here.

class BaseModel(models.Model):
    """
    Description: Abstract Base model for all models
    """

    id = models.CharField(primary_key=True, unique=True, editable=False, max_length=36, default=uuid4)

    created_ts = models.DateTimeField(auto_now_add=True)
    update_ts = models.DateTimeField(auto_now=True)

    @classmethod
    def create(cls,**kwargs):
        obj = cls(kwargs)
        obj.save()
        return obj
    
    

    class Meta:
        abstract = True

    def update_fields(self, obj, **kwargs):
        """
        Used to update the specified fields
        """
        fields = []
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(obj, key, value)
                fields.append(key)

        obj.save(update_fields = fields)
