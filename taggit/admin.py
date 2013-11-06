from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from taggit.models import Tag, TaggedItem


def tagged_items_count(obj):
    tagged_items_count = TaggedItem.objects.filter(tag=obj).count()
    return tagged_items_count
tagged_items_count.short_description = _("Tagged Items Count")


class TaggedItemInline(admin.StackedInline):
    model = TaggedItem
    extra = 0


class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', tagged_items_count)
    list_filter = ('namespace',)
    ordering = ('name',)
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    list_per_page = 50
    inlines = [
        TaggedItemInline
    ]


admin.site.register(Tag, TagAdmin)
admin.site.register(TaggedItem)
