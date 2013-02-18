from django import forms
from django.core.urlresolvers import reverse
from django.conf import settings
from django.utils import simplejson
from django.utils.html import escapejs
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from taggit.utils import edit_string_for_tags


class TagAutocomplete(forms.TextInput):
    input_type = 'text'
    
    def render(self, name, value, attrs=None):
        if attrs is not None:
            attrs = dict(self.attrs.items() + attrs.items())
        list_view = reverse('taggit-list')
        if value is not None and not isinstance(value, basestring):
            value = [edit_string_for_tags([o.tag]) for o in value.select_related("tag")]
        else:
            if value is not None:
                value = value.split(',')
            else:
                value = []
        
        allow_add_attr = self.attrs.pop('allow_add', False)
        if attrs and 'allow_add' in attrs:
            allow_add_attr = attrs.pop('allow_add', False)
        
        html = super(TagAutocomplete, self).render(
            name+"_dummy",
            ",".join(value),
            attrs
        )
        if allow_add_attr is True:
            allow_add = "true"
        else:
            allow_add = "false"
        js_config = u"""{startText: "%s", \
            preFill: prefill, \
            allowAdd: %s, \
            allowAddMessage: "%s"}""" % (
                escapejs(_("Enter Tag Here")),
                allow_add,
                escapejs(_("Please choose an existing tag")),
            )
        js = u"""<script type="text/javascript">jQuery = django.jQuery; \
            jQuery().ready(function() { \
            var prefill = [];
            jQuery.each(jQuery('input[name="%s_dummy"]').val().split(','),function(i,v){prefill.push({'value': v})});
            jQuery("#%s").autoSuggest("%s", \
            %s); });</script>""" % (
                name,
                attrs['id'],
                list_view,
                js_config
            )
        return mark_safe("\n".join([html, js]))
    
    class Media:
        js_base_url = getattr(
            settings,
            'TAGGIT_AUTOCOMPLETE_JS_BASE_URL',
            '%sjquery-autocomplete' % settings.STATIC_URL)
        css = {
            'all': ('%s/css/autoSuggest.css' % js_base_url,)
        }
        js = (
            '%s/js/jquery.autoSuggest.js' % js_base_url,
        )