from django.contrib import admin
from .models import Menu, MenuItem
from django.utils.html import format_html
from django import forms

class MenuItemInlineForm(forms.ModelForm):
    class Meta:
        model = MenuItem
        fields = '__all__'


class MenuItemInline(admin.TabularInline):
    model = MenuItem
    extra = 0
    form = MenuItemInlineForm
    fields = ('title', 'parent', 'order', 'external_url', 'named_url', 'named_args', 'named_kwargs', 'open_in_new_tab')
    autocomplete_fields = ('parent',) 
    
@admin.register(Menu)
class MenuAdmin(admin.ModelAdmin):
    list_display = ('name', 'title')
    inlines = (MenuItemInline,)

@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'menu', 'parent', 'order', 'preview_url')
    list_filter = ('menu',)
    search_fields = ('title', 'external_url', 'named_url')

    def preview_url(self, obj):
        url = obj.get_resolved_url()
        if url:
            return format_html('<a href="{}" target="_blank">preview</a>', url)
        return "-"
    preview_url.short_description = "URL"