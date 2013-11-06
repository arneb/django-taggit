from django.contrib.contenttypes.generic import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models.fields.related import ManyToManyRel, RelatedField, \
    add_lazy_relation
from django.db.models.related import RelatedObject
from django.utils.translation import ugettext_lazy as _
from taggit import settings
from taggit.forms import TagField
from taggit.models import TaggedItem, GenericTaggedItemBase
from taggit.utils import require_instance_manager
from taggit.widgets import TagAutocomplete
try:
    from django.db.models.related import PathInfo
except ImportError:
    pass


class JoiningObject(object):
    def __init__(self, model, through, direct):
        self.model = model
        self.through = through
        self.direct = direct

    #This is required because of comparing join fields in
    #django.db.models.sql.query.Query.join method
    def __eq__(self, other):
        return isinstance(other, JoiningObject) and self.model == other.model and self.through == other.through and self.direct == other.direct

    def __ne__(self, other):
        return not self == other

    #Classes which define custom __eq__, must either also define __hash__
    #or explicitly mark themselves as unhashable. We do the latter.
    __hash__ = None

    def get_extra_join_sql(self, connection, qn, lhs_alias, rhs_alias):
        if self.direct:
            alias_to_join = rhs_alias
        else:
            alias_to_join = lhs_alias
        extra_col = self.through._meta.get_field_by_name('content_type')[0].column
        content_type_ids = [ContentType.objects.get_for_model(subclass).pk for subclass in _get_subclasses(self.model)]
        if len(content_type_ids) == 1:
            content_type_id = content_type_ids[0]
            extra_where = " AND %s.%s = %%s" % (qn(alias_to_join), qn(extra_col))
            params = [content_type_id]
        else:
            extra_where = " AND %s.%s IN (%s)" % (qn(alias_to_join), qn(extra_col), ','.join(['%s']*len(content_type_ids)))
            params = content_type_ids
        return extra_where, params


class TaggableRel(ManyToManyRel):
    def __init__(self, related_name=None):
        super(TaggableRel, self).__init__(None, related_name)
        self.related_name = related_name
        self.limit_choices_to = {}
        self.symmetrical = True
        self.multiple = True
        self.through = None


class TaggableManager(RelatedField):
    def __init__(self, verbose_name=_("Tags"),
        help_text=_("A comma-separated list of tags."), through=None, blank=False, related_name=None):
        self.through = through or TaggedItem
        self.rel = TaggableRel(related_name)
        self.verbose_name = verbose_name
        self.help_text = help_text
        self.blank = blank
        self.editable = True
        self.unique = False
        self.creates_table = False
        self.db_column = None
        self.choices = None
        self.serialize = False
        self.null = True
        self.creation_counter = models.Field.creation_counter
        self.related_name = related_name
        models.Field.creation_counter += 1

    def __get__(self, instance, model):
        if instance is not None and instance.pk is None:
            raise ValueError("%s objects need to have a primary key value "
                "before you can access their tags." % model.__name__)
        manager = _TaggableManager(
            through=self.through, model=model, instance=instance
        )
        return manager

    def contribute_to_class(self, cls, name):
        self.name = self.column = name
        self.model = cls
        cls._meta.add_field(self)
        setattr(cls, name, self)
        if not cls._meta.abstract:
            if isinstance(self.through, basestring):
                def resolve_related_class(field, model, cls):
                    self.through = model
                    self.post_through_setup(cls)
                add_lazy_relation(
                    cls, self, self.through, resolve_related_class
                )
            else:
                self.post_through_setup(cls)

    def post_through_setup(self, cls):
        self.related = RelatedObject(cls, self.model, self)
        self.use_gfk = (
            self.through is None or issubclass(self.through, GenericTaggedItemBase)
        )
        self.rel.to = self.through._meta.get_field("tag").rel.to
        if self.use_gfk:
            tagged_items = GenericRelation(self.through, related_name=self.related_name)
            tagged_items.contribute_to_class(cls, "tagged_items")

    def save_form_data(self, instance, value):
        getattr(instance, self.name).set(*value)

    def formfield(self, form_class=TagField, **kwargs):
        defaults = {
            "label": self.verbose_name,
            "help_text": self.help_text,
            "required": not self.blank,
        }
        if settings.TAGGIT_AUTOCOMPLETE_WIDGET:
            defaults["widget"] = TagAutocomplete

        defaults.update(kwargs)
        return form_class(**defaults)

    def value_from_object(self, instance):
        if instance.pk:
            return self.through.objects.filter(**self.through.lookup_kwargs(instance))
        return self.through.objects.none()

    def related_query_name(self):
        return self.model._meta.module_name

    def m2m_reverse_name(self):
        return self.through._meta.get_field_by_name("tag")[0].column

    def m2m_reverse_field_name(self):
        return self.through._meta.get_field_by_name("tag")[0].name

    def m2m_target_field_name(self):
        return self.model._meta.pk.name

    def m2m_reverse_target_field_name(self):
        return self.rel.to._meta.pk.name

    def m2m_column_name(self):
        if self.use_gfk:
            return self.through._meta.virtual_fields[0].fk_field
        return self.through._meta.get_field('content_object').column

    def db_type(self, connection=None):
        return None

    def m2m_db_table(self):
        return self.through._meta.db_table

    def bulk_related_objects(self, new_objs, using):
        return []

    #This method is only used in django <= 1.5
    def extra_filters(self, pieces, pos, negate):
        if negate or not self.use_gfk:
            return []
        prefix = "__".join(pieces[:pos] + ["tagged_items"] + pieces[:2*pos-2])
        cts = map(ContentType.objects.get_for_model, _get_subclasses(self.model))
        if len(cts) == 1:
            return [("%s__content_type" % prefix, cts[0])]
        return [("%s__content_type__in" % prefix, cts)]

    #This and all the methods till the end of class are only used in django >= 1.6
    def _get_mm_case_path_info(self, direct=False):
        pathinfos = []
        linkfield1 = self.through._meta.get_field_by_name('content_object')[0]
        linkfield2 = self.through._meta.get_field_by_name(self.m2m_reverse_field_name())[0]
        if direct:
            join1infos, _, _, _ = linkfield1.get_reverse_path_info()
            join2infos, opts, target, final = linkfield2.get_path_info()
        else:
            join1infos, _, _, _ = linkfield2.get_reverse_path_info()
            join2infos, opts, target, final = linkfield1.get_path_info()
        pathinfos.extend(join1infos)
        pathinfos.extend(join2infos)
        return pathinfos, opts, target, final

    def _get_gfk_case_path_info(self, direct=False):
        pathinfos = []
        from_field = self.model._meta.pk
        opts = self.through._meta
        object_id_field = opts.get_field_by_name('object_id')[0]
        linkfield = self.through._meta.get_field_by_name(self.m2m_reverse_field_name())[0]
        if direct:
            joining_object = JoiningObject(self.model, self.through, True)
            join1infos = [PathInfo(from_field, object_id_field, self.model._meta, opts, joining_object, True, False)]
            join2infos, opts, target, final = linkfield.get_path_info()
        else:
            joining_object = JoiningObject(self.model, self.through, False)
            join1infos, _, _, _ = linkfield.get_reverse_path_info()
            join2infos = [PathInfo(object_id_field, from_field, opts, self.model._meta, joining_object, True, False)]
            target = from_field
            final = self
            opts = self.model._meta

        pathinfos.extend(join1infos)
        pathinfos.extend(join2infos)
        return pathinfos, opts, target, final

    def get_path_info(self):
        if self.use_gfk:
            return self._get_gfk_case_path_info(direct=True)
        else:
            return self._get_mm_case_path_info(direct=True)

    def get_reverse_path_info(self):
        if self.use_gfk:
            return self._get_gfk_case_path_info(direct=False)
        else:
            return self._get_mm_case_path_info(direct=False)


class _TaggableManager(models.Manager):
    def __init__(self, through, model, instance):
        self.through = through
        self.model = model
        self.instance = instance
        self.force_lowercase = settings.TAGGIT_FORCE_LOWERCASE

    def get_query_set(self):
        return self.through.tags_for(self.model, self.instance)

    def _lookup_kwargs(self):
        return self.through.lookup_kwargs(self.instance)

    @require_instance_manager
    def add(self, *tags):
        if not tags:
            return

        str_tags = set()
        obj_tags = set()

        for one in tags:
            if not isinstance(one, basestring):
                obj_tags.add(one)
            else:
                value = one.lower() if self.force_lowercase else one
                str_tags.add(value)

        if str_tags:
            existing = self.through.tag_model().objects.all()
            q = models.Q()
            for one in str_tags:
                q |= models.Q(name__exact=one)

            existing = existing.filter(q)
            obj_tags.update(existing)

        to_create = str_tags - set([one.name for one in obj_tags])
        for new_name in to_create:
            x = self.through.tag_model().objects.create(name=new_name)
            obj_tags.add(x)

        for tag in obj_tags:
            self.through.objects.get_or_create(tag=tag, **self._lookup_kwargs())

    @require_instance_manager
    def set(self, *tags):
        have = set(tag.name for tag in self.get_query_set().all())
        wanted = set([tag.name if isinstance(tag, self.through.tag_model()) else tag for tag in tags])

        add = wanted - have
        remove = have - wanted

        self.add(*list(add))
        self.remove(*list(remove))

    @require_instance_manager
    def remove(self, *tags):
        if not tags:
            return

        filter_props = self._lookup_kwargs()
        filter_props['tag__name__%sregex' % ('i' if self.force_lowercase else '')] = r'(^' + '$|^'.join(tags) + '$)'
        self.through.objects.filter(**filter_props).delete()

    @require_instance_manager
    def clear(self):
        self.through.objects.filter(**self._lookup_kwargs()).delete()

    def most_common(self):
        return self.get_query_set().annotate(
            num_times=models.Count(self.through.tag_relname())
        ).order_by('-num_times')

    @require_instance_manager
    def similar_objects(self, num=None, **filters):
        lookup_kwargs = self._lookup_kwargs()
        lookup_keys = sorted(lookup_kwargs)
        qs = self.through.objects.values(*lookup_kwargs.keys())
        qs = qs.annotate(n=models.Count('pk'))
        qs = qs.exclude(**lookup_kwargs)
        subq = self.all()
        qs = qs.filter(tag__in=list(subq))
        qs = qs.order_by('-n')

        if filters is not None:
            qs = qs.filter(**filters)

        if num is not None:
            qs = qs[:num]

        # TODO: This all feels like a bit of a hack.
        items = {}
        if len(lookup_keys) == 1:
            # Can we do this without a second query by using a select_related()
            # somehow?
            f = self.through._meta.get_field_by_name(lookup_keys[0])[0]
            objs = f.rel.to._default_manager.filter(**{
                "%s__in" % f.rel.field_name: [r["content_object"] for r in qs]
            })
            for obj in objs:
                items[(getattr(obj, f.rel.field_name),)] = obj
        else:
            preload = {}
            for result in qs:
                preload.setdefault(result['content_type'], set())
                preload[result["content_type"]].add(result["object_id"])

            for ct, obj_ids in preload.iteritems():
                ct = ContentType.objects.get_for_id(ct)
                for obj in ct.model_class()._default_manager.filter(pk__in=obj_ids):
                    items[(ct.pk, obj.pk)] = obj

        results = []
        for result in qs:
            obj = items[
                tuple(result[k] for k in lookup_keys)
            ]
            obj.similar_tags = result["n"]
            results.append(obj)
        return results

    def namespaced(self):
        return self.get_query_set().exclude(namespace='')

    def non_namespaced(self):
        return self.get_query_set().filter(namespace='')


def _get_subclasses(model):
    subclasses = [model]
    for f in model._meta.get_all_field_names():
        field = model._meta.get_field_by_name(f)[0]
        if (isinstance(field, RelatedObject) and
            getattr(field.field.rel, "parent_link", None)):
            subclasses.extend(_get_subclasses(field.model))
    return subclasses
