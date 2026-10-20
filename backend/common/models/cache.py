from django.db import models

from common.cache.manager import cache_manager


class CacheModel(models.Model):
    """Opt-in mixin — only inherit this on models that are actually read
    through the cache. Provides automatic invalidation on save()/delete()
    so call sites never need to remember to clear the cache manually."""

    class Meta:
        abstract = True

    def cache_key(self) -> str:
        return f"{self._meta.model_name}:{self.pk}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        cache_manager.delete(self.cache_key())

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        cache_manager.delete(self.cache_key())
