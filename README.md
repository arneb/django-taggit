django-taggit
=============

``django-taggit`` is a simpler approach to tagging with Django.

Getting Started
---------------

You can simply install it with
``pip``::

    $ pip install django-taggit


Add ``"taggit"`` to your
``INSTALLED_APPS`` then just add a TaggableManager to your model and go::

    from django.db import models

    from taggit.managers import TaggableManager

    class Food(models.Model):
        # ... fields here

        tags = TaggableManager()

Then you can use the API like so::

    >>> apple = Food.objects.create(name="apple")
    >>> apple.tags.add("red", "green", "delicious")
    >>> apple.tags.all()
    [<Tag: red>, <Tag: green>, <Tag: delicious>]
    
    >>> apple.tags.remove("green")
    >>> apple.tags.all()
    [<Tag: red>, <Tag: delicious>]
    
    >>> Food.objects.filter(tags__name__in=["red"])
    [<Food: apple>, <Food: cherry>]

Tags will show up for you automatically in forms and the admin.

If you want to enforce lowercase tags everywhere (recommended, to avoid
ending up with tags 'Music' and 'music' which are functionally identical
but show up in different taxonomies), add to settings.py:

``TAGGIT_FORCE_LOWERCASE = True``

If you want to prevent certain words from being added as tags (such as
English articles to, from, the, of, etc.) add to settings.py:

``TAGGIT_STOPWORDS = [u'a', u'an', u'and', u'be', u'from', u'of']``

Requirements
------------

``django-taggit`` requires Django 1.1 or greater.

Further Infos
-------------

For more info checkout out the
[documentation](http://readthedocs.org/docs/django-taggit/en/latest/).

And for questions about usage or development you can contact
the [mailinglist](http://groups.google.com/group/django-taggit).

Merger's notes
--------------

* Decided to stay with version 0.9.4 changed by shacker.
* Decided to leave markdown version of README.
* Decided not to merge forks:
    * extending base functionality or ones that would lower performance;
    * being much against PEP-8;
    * with changes solving specific problems.
* Combined alex/django-taggit & fcurella/django-taggit-autocomplete by AGoodId (https://github.com/AGoodId/django-taggit).
