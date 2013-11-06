from mock import patch

from nose import tools

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import connection, IntegrityError
from django.test import TestCase

from taggit.managers import TaggableManager
from taggit.models import Tag, TaggedItem
from taggit.utils import parse_tags, edit_string_for_tags

from forms import (FoodForm, DirectFoodForm, CustomPKFoodForm,
    OfficialFoodForm)
from models import (Food, Pet, HousePet, DirectFood, DirectPet,
    DirectHousePet, TaggedPet, CustomPKFood, CustomPKPet, CustomPKHousePet,
    TaggedCustomPKPet, OfficialFood, OfficialPet, OfficialHousePet,
    OfficialThroughModel, OfficialTag, Photo, Movie, Article)


class BaseTaggingTest(object):
    def assert_tags_equal(self, qs, tags, sort=True, attr="name"):
        got = map(lambda tag: getattr(tag, attr), qs)
        if sort:
            got.sort()
            tags.sort()
        tools.assert_equals(got, tags)

    def assert_num_queries(self, n, f, *args, **kwargs):
        original_DEBUG = settings.DEBUG
        settings.DEBUG = True
        current = len(connection.queries)
        try:
            f(*args, **kwargs)
            tools.assert_equals(
                len(connection.queries) - current,
                n,
            )
        finally:
            settings.DEBUG = original_DEBUG

    def _get_form_str(self, form_str):

        form_str %= {
            'help_start': '<span class="helptext">',
            'help_stop': '</span>'
        }
        return form_str

    def assert_form_renders(self, form, html):
        tools.assert_equals(str(form), self._get_form_str(html))


class BaseTaggingTestCase(TestCase, BaseTaggingTest):
    pass


class BaseTaggingTransactionTestCase(TestCase, BaseTaggingTest):
    pass


class TagModelTestCase(BaseTaggingTestCase):
    food_model = Food
    tag_model = Tag

    def test_unique_slug(self):
        apple = self.food_model.objects.create(name='apple')
        apple.tags.add('Red', 'red')

    def test_update(self):
        special = self.tag_model.objects.create(name='special')
        special.save()

    def test_add(self):
        apple = self.food_model.objects.create(name='apple')
        yummy = self.tag_model.objects.create(name='yummy')
        apple.tags.add(yummy)

    def test_add_twice_raises(self):
        self.tag_model.objects.create(name='apple')
        tools.assert_raises(IntegrityError, lambda: self.tag_model.objects.create(name='apple'))

    @patch('taggit.managers.settings')
    def test_slugify(self, mocked_settings):
        mocked_settings.TAGGIT_FORCE_LOWERCASE = False
        a = Article.objects.create(title='django-taggit 1.0 Released')
        a.tags.add('awesome', 'release', 'AWESOME')
        self.assert_tags_equal(a.tags.all(), [
            'category-awesome',
            'category-release',
            'category-awesome-1'
        ], attr='slug')


class TagModelDirectTestCase(TagModelTestCase):
    food_model = DirectFood
    tag_model = Tag


class TagModelCustomPKTestCase(TagModelTestCase):
    food_model = CustomPKFood
    tag_model = Tag


class TagModelOfficialTestCase(TagModelTestCase):
    food_model = OfficialFood
    tag_model = OfficialTag


class TaggableManagerTestCase(BaseTaggingTestCase):
    food_model = Food
    pet_model = Pet
    housepet_model = HousePet
    taggeditem_model = TaggedItem
    tag_model = Tag

    def test_add_tag(self):
        apple = self.food_model.objects.create(name='apple')
        tools.assert_equals(list(apple.tags.all()), [])
        tools.assert_equals(list(self.food_model.tags.all()),  [])

        apple.tags.add('green')
        self.assert_tags_equal(apple.tags.all(), ['green'])
        self.assert_tags_equal(self.food_model.tags.all(), ['green'])

        pear = self.food_model.objects.create(name='pear')
        pear.tags.add('green')
        self.assert_tags_equal(pear.tags.all(), ['green'])
        self.assert_tags_equal(self.food_model.tags.all(), ['green'])

        apple.tags.add('red')
        self.assert_tags_equal(apple.tags.all(), ['green', 'red'])
        self.assert_tags_equal(self.food_model.tags.all(), ['green', 'red'])

        self.assert_tags_equal(
            self.food_model.tags.most_common(),
            ['green', 'red'],
            sort=False
        )

        apple.tags.remove('green')
        self.assert_tags_equal(apple.tags.all(), ['red'])
        self.assert_tags_equal(self.food_model.tags.all(), ['green', 'red'])
        tag = self.tag_model.objects.create(name='delicious')
        apple.tags.add(tag)
        self.assert_tags_equal(apple.tags.all(), ['red', 'delicious'])

        apple.tags.add('Marlene')
        self.assert_tags_equal(apple.tags.all(), ['red', 'delicious', 'Marlene'])

    @patch('taggit.managers.settings')
    def test_force_lowercase(self, mocked_settings):
        mocked_settings.TAGGIT_FORCE_LOWERCASE = True
        apple = self.food_model.objects.create(name='apple')

        apple.tags.add('Marlene')
        self.assert_tags_equal(apple.tags.all(), ['marlene'])

        apple.tags.remove('Marlene')
        self.assert_tags_equal(apple.tags.all(), [])

    def test_set_tag(self):
        banana = self.food_model.objects.create(name='banana')
        pear = self.food_model.objects.create(name='pear')

        tag = self.tag_model.objects.create(name='yellow')
        banana.tags.add(tag)
        tag2 = self.tag_model.objects.create(name='slippery')
        banana.tags.add(tag2)
        self.assert_tags_equal(self.food_model.tags.all(), ['yellow', 'slippery'])
        self.assert_tags_equal(banana.tags.all(), ['yellow', 'slippery'])

        taggeditem_banana_yellow = banana.tags.through.objects.filter(tag=tag).all()[0]
        taggeditem_banana_slippery = banana.tags.through.objects.filter(tag=tag2).all()[0]

        pear.tags.set('yellow','slippery')
        self.assert_tags_equal(self.food_model.tags.all(), ['yellow', 'slippery'])
        self.assert_tags_equal(pear.tags.all(), ['yellow', 'slippery'])

        taggeditem_pear_yellow = pear.tags.through.objects.filter(tag=tag).all()[0]
        taggeditem_pear_slippery = pear.tags.through.objects.filter(tag=tag2).all()[0]

        banana.tags.set(tag2,tag, 'funny', 'sweet', 'crazy', 'fruit')
        self.assert_tags_equal(banana.tags.all(), ['yellow', 'slippery', 'funny', 'sweet', 'crazy', 'fruit'])
        self.assert_tags_equal(pear.tags.all(), ['yellow', 'slippery'])

        # Test that the primary keys in the TaggedItem model are preserved
        tools.assert_equals(banana.tags.through.objects.filter(tag=tag).all()[0].pk, taggeditem_banana_yellow.id)
        tools.assert_equals(banana.tags.through.objects.filter(tag=tag2).all()[0].pk, taggeditem_banana_slippery.id)
        tools.assert_equals(pear.tags.through.objects.filter(tag=tag).all()[0].pk, taggeditem_pear_yellow.id)
        tools.assert_equals(pear.tags.through.objects.filter(tag=tag2).all()[0].pk, taggeditem_pear_slippery.id)

        banana.tags.set()
        self.assert_tags_equal(banana.tags.all(), [])

    def test_add_queries(self):
        apple = self.food_model.objects.create(name="apple")
        #   1 query to see which tags exist
        # + 3 queries to create the tags.
        # + 6 queries to create the intermediary things (including SELECTs, to
        #     make sure we don't double create.
        self.assert_num_queries(10, apple.tags.add, "red", "delicious", "green")

        pear = self.food_model.objects.create(name="pear")
        #   1 query to see which tags exist
        # + 4 queries to create the intermeidary things (including SELECTs, to
        #   make sure we dont't double create.
        self.assert_num_queries(5, pear.tags.add, "green", "delicious")

        self.assert_num_queries(0, pear.tags.add)

    def test_require_pk(self):
        food_instance = self.food_model()
        self.assertRaises(ValueError, lambda: food_instance.tags.all())

    def test_delete_obj(self):
        apple = self.food_model.objects.create(name="apple")
        apple.tags.add("red")
        self.assert_tags_equal(apple.tags.all(), ["red"])
        strawberry = self.food_model.objects.create(name="strawberry")
        strawberry.tags.add("red")
        apple.delete()
        self.assert_tags_equal(strawberry.tags.all(), ["red"])

    def test_delete_bulk(self):
        apple = self.food_model.objects.create(name="apple")
        kitty = self.pet_model.objects.create(pk=apple.pk,  name="kitty")

        apple.tags.add("red", "delicious", "fruit")
        kitty.tags.add("feline")

        self.food_model.objects.all().delete()

        self.assert_tags_equal(kitty.tags.all(), ["feline"])

    def test_lookup_by_tag(self):
        apple = self.food_model.objects.create(name="apple")
        apple.tags.add("red", "green")
        pear = self.food_model.objects.create(name="pear")
        pear.tags.add("green")

        tools.assert_equals(
            list(self.food_model.objects.filter(tags__name__in=["red"])),
            [apple]
        )
        tools.assert_equals(
            list(self.food_model.objects.filter(tags__name__in=["green"])),
            [apple, pear]
        )
        tools.assert_equals(
            list(self.food_model.objects.filter(tags__name__in = ['green']).filter(tags__name__in = ['red'])),
            [apple]
        )

        kitty = self.pet_model.objects.create(name="kitty")
        kitty.tags.add("fuzzy", "red")
        dog = self.pet_model.objects.create(name="dog")
        dog.tags.add("woof", "red")
        tools.assert_equals(
            list(self.food_model.objects.filter(tags__name__in=["red"]).distinct()),
            [apple]
        )

        tag = self.tag_model.objects.get(name="woof")
        tools.assert_equals(list(self.pet_model.objects.filter(tags__in=[tag])), [dog])

        cat = self.housepet_model.objects.create(name="cat", trained=True)
        cat.tags.add("fuzzy")

        tools.assert_equals(
            set(map(lambda o: o.pk, self.pet_model.objects.filter(tags__name__in=["fuzzy"]))),
            set([kitty.pk, cat.pk])
        )
        

    def test_lookup_bulk(self):
        apple = self.food_model.objects.create(name="apple")
        pear = self.food_model.objects.create(name="pear")
        apple.tags.add('fruit', 'green')
        pear.tags.add('fruit', 'yummie')

        def lookup_qs():
            # New fix: directly allow WHERE object_id IN (SELECT id FROM ..)
            objects = self.food_model.objects.all()
            lookup = self.taggeditem_model.bulk_lookup_kwargs(objects)
            list(self.taggeditem_model.objects.filter(**lookup))

        def lookup_list():
            # Simulate old situation: iterate over a list.
            objects = list(self.food_model.objects.all())
            lookup = self.taggeditem_model.bulk_lookup_kwargs(objects)
            list(self.taggeditem_model.objects.filter(**lookup))

        self.assert_num_queries(1, lookup_qs)
        self.assert_num_queries(2, lookup_list)

    def test_exclude(self):
        apple = self.food_model.objects.create(name="apple")
        apple.tags.add("red", "green", "delicious")

        pear = self.food_model.objects.create(name="pear")
        pear.tags.add("green", "delicious")

        guava = self.food_model.objects.create(name="guava")

        tools.assert_equals(
            set(map(lambda o: o.pk, self.food_model.objects.exclude(tags__name__in=["red"]))),
            set([pear.pk, guava.pk]),
        )

    def test_similarity_by_tag(self):
        """Test that pears are more similar to apples than watermelons"""
        apple = self.food_model.objects.create(name="apple")
        apple.tags.add("green", "juicy", "small", "sour")

        pear = self.food_model.objects.create(name="pear")
        pear.tags.add("green", "juicy", "small", "sweet")

        watermelon = self.food_model.objects.create(name="watermelon")
        watermelon.tags.add("green", "juicy", "large", "sweet")

        similar_objs = apple.tags.similar_objects()
        tools.assert_equals(similar_objs, [pear, watermelon])
        tools.assert_equals(map(lambda x: x.similar_tags, similar_objs), [3, 2])

    def test_tag_reuse(self):
        apple = self.food_model.objects.create(name="apple")
        apple.tags.add("juicy", "juicy")
        self.assert_tags_equal(apple.tags.all(), ['juicy'])

    def test_query_traverse(self):
        spot = self.pet_model.objects.create(name='Spot')
        spike = self.pet_model.objects.create(name='Spike')
        spot.tags.add('scary')
        spike.tags.add('fluffy')
        lookup_kwargs = {
            '%s__name' % self.pet_model._meta.module_name: 'Spot'
        }
        self.assert_tags_equal(
           self.tag_model.objects.filter(**lookup_kwargs),
           ['scary']
        )

    def test_taggeditem_unicode(self):
        ross = self.pet_model.objects.create(name="ross")
        # I keep Ross Perot for a pet, what's it to you?
        ross.tags.add("president")

        tools.assert_equals(
            unicode(self.taggeditem_model.objects.all()[0]),
            "ross tagged with president"
        )

    def test_abstract_subclasses(self):
        p = Photo.objects.create()
        p.tags.add("outdoors", "pretty")
        self.assert_tags_equal(
            p.tags.all(),
            ["outdoors", "pretty"]
        )

        m = Movie.objects.create()
        m.tags.add("hd")
        self.assert_tags_equal(
            m.tags.all(),
            ["hd"],
        )


class TaggableManagerDirectTestCase(TaggableManagerTestCase):
    food_model = DirectFood
    pet_model = DirectPet
    housepet_model = DirectHousePet
    taggeditem_model = TaggedPet


class TaggableManagerCustomPKTestCase(TaggableManagerTestCase):
    food_model = CustomPKFood
    pet_model = CustomPKPet
    housepet_model = CustomPKHousePet
    taggeditem_model = TaggedCustomPKPet

    def test_require_pk(self):
        # TODO with a charfield pk, pk is never None, so taggit has no way to
        # tell if the instance is saved or not
        pass


class TaggableManagerOfficialTestCase(TaggableManagerTestCase):
    food_model = OfficialFood
    pet_model = OfficialPet
    housepet_model = OfficialHousePet
    taggeditem_model = OfficialThroughModel
    tag_model = OfficialTag

    def test_extra_fields(self):
        self.tag_model.objects.create(name="red")
        self.tag_model.objects.create(name="delicious", official=True)
        apple = self.food_model.objects.create(name="apple")
        apple.tags.add("delicious", "red")

        pear = self.food_model.objects.create(name="Pear")
        pear.tags.add("delicious")

        tools.assert_equals(
            map(lambda o: o.pk, self.food_model.objects.filter(tags__official=False)),
            [apple.pk],
        )


class TaggableFormTestCase(BaseTaggingTestCase):
    form_class = FoodForm
    food_model = Food

    def test_form(self):
        tools.assert_equals(self.form_class.base_fields.keys(), ['name', 'tags'])

        f = self.form_class({'name': 'apple', 'tags': 'green, red, yummy'})
        tools.assert_equals(f.fields.keys(), ['name', 'tags'])

        #...orly?! Django 1.4 renders form differently (input attrs order...)
        '''

        self.assert_form_renders(f, """<tr><th><label for="id_name">Name:</label></th><td><input id="id_name" type="text" name="name" value="apple" maxlength="50" /></td></tr>
<tr><th><label for="id_tags">Tags:</label></th><td><input class="taggit-tags" type="text" name="tags" value="green, red, yummy" id="id_tags" /><br />%(help_start)sA comma-separated list of tags.%(help_stop)s</td></tr>""")
        '''
        f.save()

        apple = self.food_model.objects.get(name='apple')
        self.assert_tags_equal(apple.tags.all(), ['green', 'red', 'yummy'])

        f = self.form_class({'name': 'apple', 'tags': 'green, red, yummy, delicious'}, instance=apple)
        f.save()
        apple = self.food_model.objects.get(name='apple')
        self.assert_tags_equal(apple.tags.all(), ['green', 'red', 'yummy', 'delicious'])
        tools.assert_equals(self.food_model.objects.count(), 1)

        f = self.form_class({"name": "raspberry"})
        self.assertFalse(f.is_valid())

        f = self.form_class(instance=apple)
        '''
        self.assert_form_renders(f, """<tr><th><label for="id_name">Name:</label></th><td><input id="id_name" type="text" name="name" value="apple" maxlength="50" /></td></tr>
<tr><th><label for="id_tags">Tags:</label></th><td><input class="taggit-tags" type="text" name="tags" value="delicious, green, red, yummy" id="id_tags" /><br />%(help_start)sA comma-separated list of tags.%(help_stop)s</td></tr>""")
        '''

        apple.tags.add('has,comma')
        f = self.form_class(instance=apple)
        '''
        self.assert_form_renders(f, """<tr><th><label for="id_name">Name:</label></th><td><input id="id_name" type="text" name="name" value="apple" maxlength="50" /></td></tr>
<tr><th><label for="id_tags">Tags:</label></th><td><input class="taggit-tags" type="text" name="tags" value="&quot;has,comma&quot;, delicious, green, red, yummy" id="id_tags" /><br />%(help_start)sA comma-separated list of tags.%(help_stop)s</td></tr>""")
        '''

        apple.tags.add('has space')
        f = self.form_class(instance=apple)
        '''
        self.assert_form_renders(f, """<tr><th><label for="id_name">Name:</label></th><td><input id="id_name" type="text" name="name" value="apple" maxlength="50" /></td></tr>
<tr><th><label for="id_tags">Tags:</label></th><td><input class="taggit-tags" type="text" name="tags" value="&quot;has space&quot;, &quot;has,comma&quot;, delicious, green, red, yummy" id="id_tags" /><br />%(help_start)sA comma-separated list of tags.%(help_stop)s</td></tr>""")
        '''

    def test_formfield(self):
        tm = TaggableManager(verbose_name='categories', help_text='Add some categories', blank=True)
        ff = tm.formfield()
        tools.assert_equals(ff.label, 'categories')
        tools.assert_equals(ff.help_text, u'Add some categories')
        tools.assert_equals(ff.required, False)

        tools.assert_equals(ff.clean(""), [])

        tm = TaggableManager()
        ff = tm.formfield()
        self.assertRaises(ValidationError, ff.clean, "")


class TaggableFormDirectTestCase(TaggableFormTestCase):
    form_class = DirectFoodForm
    food_model = DirectFood


class TaggableFormCustomPKTestCase(TaggableFormTestCase):
    form_class = CustomPKFoodForm
    food_model = CustomPKFood


class TaggableFormOfficialTestCase(TaggableFormTestCase):
    form_class = OfficialFoodForm
    food_model = OfficialFood


class TagStringParseTestCase(TestCase):
    """
    Ported from Jonathan Buchanan's `django-tagging
    <http://django-tagging.googlecode.com/>`_
    """

    def test_with_simple_space_delimited_tags(self):
        """
        Test with simple space-delimited tags.
        """
        tools.assert_equals(parse_tags('one'), [u'one'])
        tools.assert_equals(parse_tags('one two'), [u'one', u'two'])
        tools.assert_equals(parse_tags('one two three'), [u'one', u'three', u'two'])
        tools.assert_equals(parse_tags('one one two two'), [u'one', u'two'])

    @patch('taggit.utils.settings')
    def test_with_simple_space_delimited_tags_disabled_space_split(self, mocked_settings):
        mocked_settings.TAGGIT_ENABLE_SPACE_SPLIT_IF_NOT_QUOTES = False
        tools.assert_equals(parse_tags('one'), [u'one'])
        tools.assert_equals(parse_tags('one two'), [u'one two'])
        tools.assert_equals(parse_tags('one two three'), [u'one two three'])

    def test_with_comma_delimited_multiple_words(self):
        """
        Test with comma-delimited multiple words.
        An unquoted comma in the input will trigger this.
        """
        tools.assert_equals(parse_tags(',one'), [u'one'])
        tools.assert_equals(parse_tags(',one two'), [u'one two'])
        tools.assert_equals(parse_tags(',one two three'), [u'one two three'])
        tools.assert_equals(parse_tags('a-one, a-two and a-three'),
            [u'a-one', u'a-two and a-three'])

    @patch('taggit.utils.settings')
    def test_with_comma_delimited_multiple_words_disabled_space_split(self, mocked_settings):
        mocked_settings.TAGGIT_ENABLE_SPACE_SPLIT_IF_NOT_QUOTES = False
        tools.assert_equals(parse_tags(',one'), [u'one'])
        tools.assert_equals(parse_tags(',one two'), [u'one two'])
        tools.assert_equals(parse_tags(',one two three'), [u'one two three'])
        tools.assert_equals(parse_tags('a one, a-two and a-three'),
            [u'a one', u'a-two and a-three'])

    def test_with_double_quoted_multiple_words(self):
        """
        Test with double-quoted multiple words.
        A completed quote will trigger this.  Unclosed quotes are ignored.
        """
        tools.assert_equals(parse_tags('"one'), [u'one'])
        tools.assert_equals(parse_tags('"one two'), [u'one', u'two'])
        tools.assert_equals(parse_tags('"one two three'), [u'one', u'three', u'two'])
        tools.assert_equals(parse_tags('"one two"'), [u'one two'])
        tools.assert_equals(parse_tags('a-one "a-two and a-three"'),
            [u'a-one', u'a-two and a-three'])

    @patch('taggit.utils.settings')
    def test_with_double_quoted_multiple_words_disabled_space_split(self, mocked_settings):
        mocked_settings.TAGGIT_ENABLE_SPACE_SPLIT_IF_NOT_QUOTES = False
        tools.assert_equals(parse_tags('"one two"'), [u'one two'])
        tools.assert_equals(parse_tags('a one "a-two and a-three"'),
            [u'a one', u'a-two and a-three'])

    def test_with_no_loose_commas(self):
        """
        Test with no loose commas -- split on spaces.
        """
        tools.assert_equals(parse_tags('one two "thr,ee"'), [u'one', u'thr,ee', u'two'])

    @patch('taggit.utils.settings')
    def test_with_no_loose_commas_disabled_space_split(self, mocked_settings):
        mocked_settings.TAGGIT_ENABLE_SPACE_SPLIT_IF_NOT_QUOTES = False
        tools.assert_equals(parse_tags('one two "thr,ee"'), [u'one two', u'thr,ee'])

    def test_with_loose_commas(self):
        """
        Loose commas - split on commas
        """
        tools.assert_equals(parse_tags('"one", two three'), [u'one', u'two three'])

    @patch('taggit.utils.settings')
    def test_with_loose_commas_disabled_space_split(self, mocked_settings):
        mocked_settings.TAGGIT_ENABLE_SPACE_SPLIT_IF_NOT_QUOTES = False
        tools.assert_equals(parse_tags('"one", two three'), [u'two three', u'one'])

    def test_tags_with_double_quotes_can_contain_commas(self):
        """
        Double quotes can contain commas
        """
        tools.assert_equals(parse_tags('a-one "a-two, and a-three"'),
            [u'a-one', u'a-two, and a-three'])
        tools.assert_equals(parse_tags('"two", one, one, two, "one"'),
            [u'one', u'two'])

    @patch('taggit.utils.settings')
    def test_tags_with_double_quotes_can_contain_commas_disabled_space_split(self, mocked_settings):
        mocked_settings.TAGGIT_ENABLE_SPACE_SPLIT_IF_NOT_QUOTES = False
        tools.assert_equals(parse_tags('a-one "a-two, and a-three"'),
            [u'a-one', u'a-two, and a-three'])
        tools.assert_equals(parse_tags('"two", one, one, two, "one"'),
            [u'two', u'one'])

    def test_with_naughty_input(self):
        """
        Test with naughty input.
        """
        # Bad users! Naughty users!
        tools.assert_equals(parse_tags(None), [])
        tools.assert_equals(parse_tags(''), [])
        tools.assert_equals(parse_tags('"'), [])
        tools.assert_equals(parse_tags('""'), [])
        tools.assert_equals(parse_tags('"' * 7), [])
        tools.assert_equals(parse_tags(',,,,,,'), [])
        tools.assert_equals(parse_tags('",",",",",",","'), [u','])
        tools.assert_equals(parse_tags('a-one "a-two" and "a-three'),
            [u'a-one', u'a-three', u'a-two', u'and'])

    def test_recreation_of_tag_list_string_representations(self):
        plain = Tag.objects.create(name='plain')
        spaces = Tag.objects.create(name='spa ces')
        comma = Tag.objects.create(name='com,ma')
        tools.assert_equals(edit_string_for_tags([plain]), u'plain')
        tools.assert_equals(edit_string_for_tags([plain, spaces]), u'"spa ces", plain')
        tools.assert_equals(edit_string_for_tags([plain, spaces, comma]), u'"com,ma", "spa ces", plain')
        tools.assert_equals(edit_string_for_tags([plain, comma]), u'"com,ma", plain')
        tools.assert_equals(edit_string_for_tags([comma, spaces]), u'"com,ma", "spa ces"')
