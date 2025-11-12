from django.db import models
from django.urls import reverse, NoReverseMatch
from django.utils.translation import gettext_lazy as _
import json

# Поддержка JSONField для разных версий Django
try:
    JSONField = models.JSONField 
except AttributeError:
    class JSONField(models.TextField):
        pass

class Menu(models.Model):
    name = models.SlugField(max_length=100, unique=True, help_text="Internal name used in template tag")
    title = models.CharField(max_length=200, blank=True)

    class Meta:
        verbose_name = _("Menu")
        verbose_name_plural = _("Menus")

    def __str__(self):
        return self.title or self.name


class MenuItem(models.Model):
    menu = models.ForeignKey(Menu, related_name='items', on_delete=models.CASCADE)
    parent = models.ForeignKey('self', related_name='children', on_delete=models.CASCADE, null=True, blank=True)
    title = models.CharField(max_length=200)

    external_url = models.CharField(max_length=1024, blank=True, help_text="Явный URL, например /about/ или https://...")
    named_url = models.CharField(max_length=255, blank=True, help_text="Имя url (reverse name), например 'app:view_name'")
    named_args = JSONField(blank=True, null=True, help_text="Позиционные args для reverse в виде JSON-массива, например [1]")
    named_kwargs = JSONField(blank=True, null=True, help_text="Ключевые kwargs для reverse в виде JSON-объекта, например {\"slug\": \"x\"}")

    order = models.IntegerField(default=0, help_text="Порядок сортировки в одном уровне")
    open_in_new_tab = models.BooleanField(default=False, help_text="Открывать ссылку в новой вкладке")

    class Meta:
        ordering = ('order', 'id')
        verbose_name = _("Menu item")
        verbose_name_plural = _("Menu items")

    def __str__(self):
        return self.title

    def get_resolved_url(self):
        # named_url
        if self.named_url:
            args = self.named_args or []
            kwargs = self.named_kwargs or {}
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except Exception:
                    args = []
            if isinstance(kwargs, str):
                try:
                    kwargs = json.loads(kwargs)
                except Exception:
                    kwargs = {}
            try:
                return reverse(self.named_url, args=tuple(args), kwargs=kwargs)
            except NoReverseMatch:
                return None
            except Exception:
                return None
        if self.external_url:
            return self.external_url
        return None