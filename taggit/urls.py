from django.conf.urls.defaults import patterns, url


urlpatterns = patterns(
    'taggit.views',
    url(r'^list$', 'list_tags', name='taggit-list'),
    url(r'^static/(?P<path>.*)$', 'media', name='taggit-static'),
    url(r'^ajax$', 'ajax', name='taggit-ajax'),
)
