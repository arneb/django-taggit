from django.contrib.contenttypes.models import ContentType
from django.core import serializers
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import simplejson
from django.utils.datastructures import MultiValueDictKeyError
from django.views.generic import ListView

from taggit.models import TaggedItem, Tag
from taggit.utils import edit_string_for_tags


class TaggedObjectListView(ListView):
    """Return all objects (from model or queryset) with specified tag"""
    def get(self, request, *args, **kwargs):
        slug = kwargs.get('slug')
        self.tag = get_object_or_404(Tag, slug=slug)
        self.object_list = self.get_queryset()
        context = self.get_context_data(object_list=self.object_list)
        return self.render_to_response(context)

    def get_queryset(self):
        original_queryset = super(ListView, self).get_queryset()
        queryset = original_queryset.filter(pk__in=TaggedItem.objects.filter(
            tag=self.tag,
            content_type=ContentType.objects.get_for_model(original_queryset.model)
        ).values_list("object_id", flat=True))
        return queryset

    def get_context_data(self, **kwargs):
        context = super(ListView, self).get_context_data(**kwargs)
        context['tag'] = self.tag
        return context


def list_tags(request):
    try:
        tags = Tag.objects.filter(name__icontains=request.GET['q'])
        data = [{'value': edit_string_for_tags([t]), 'name': t.name} for t in tags]
    except MultiValueDictKeyError:
        data = ""
    return HttpResponse(simplejson.dumps(data), content_type='application/json')


def ajax(request):
    """Get all of the tags available and return as a json array"""
    data = serializers.serialize('json', Tag.objects.order_by('slug').all(),
        fields=('name'), ensure_ascii=False)
    return HttpResponse(data, content_type='application/json')


def media(request, path):
    from django.views.static import serve
    from taggit.settings import TAGGIT_MEDIA_DIR
    return serve(request, path, TAGGIT_MEDIA_DIR)
