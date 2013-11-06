from django import forms
from django.core.urlresolvers import reverse
from django.conf import settings
from django.utils.html import escapejs
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from taggit.utils import edit_string_for_tags, parse_tags


class TagAutocomplete(forms.TextInput):
    input_type = 'text'

    def render(self, name, value, attrs=None):
        if attrs is not None:
            attrs = dict(self.attrs.items() + attrs.items())
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
            "%s_dummy" % name,
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
            %s);});</script>""" % (
                name,
                attrs['id'],
                reverse('taggit-list'),
                js_config
            )
        return mark_safe("\n".join([html, js]))

    def _has_changed(self, initial, data):
        """
        Called by BaseForm._get_changed_data, which sends this the form's initial value
        for the field and the raw value that was submitted to the form, *before it has
        been through any clean() methods.*

        This means that the initial data will (usually) be a related Tag manager, while
        the raw data will (usually) be a string. So, they're both converted to strings
        before sending them to the regular change comparison.
        """
        if initial is not None and not isinstance(initial, basestring):
            initial = edit_string_for_tags([o.tag for o in initial.select_related("tag")])

        if data is not None and not isinstance(data, basestring):
            data = edit_string_for_tags([o.tag for o in data.select_related("tag")])
        
        if data is not None and isinstance(data, basestring):
            data = edit_string_for_tags(parse_tags(data))
            
        return super(TagAutocomplete, self)._has_changed(initial, data)

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
