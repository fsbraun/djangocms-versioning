import copy

from django.apps import apps

from cms.models import PageContent, Placeholder
from cms.test_utils.testcases import CMSTestCase

from djangocms_versioning.constants import ARCHIVED, PUBLISHED
from djangocms_versioning.datastructures import VersionableItem, default_copy
from djangocms_versioning.models import Version
from djangocms_versioning.test_utils.factories import PollVersionFactory
from djangocms_versioning.test_utils.people.models import PersonContent
from djangocms_versioning.test_utils.polls.models import Poll, PollContent
from djangocms_versioning.test_utils.text.models import Text
from djangocms_versioning.test_utils.unversioned_editable_app.models import FancyPoll


class VersionableItemTestCase(CMSTestCase):
    def setUp(self):
        self.initial_version = PollVersionFactory()

    def test_distinct_groupers(self):
        latest_poll1_version = PollVersionFactory(
            content__poll=self.initial_version.content.poll
        )
        poll2_version = PollVersionFactory()
        PollVersionFactory(content__poll=poll2_version.content.poll)
        latest_poll2_version = PollVersionFactory(
            content__poll=poll2_version.content.poll
        )

        versionable = VersionableItem(
            content_model=PollContent,
            grouper_field_name="poll",
            copy_function=default_copy,
        )
        self.assertQuerysetEqual(
            versionable.distinct_groupers(),
            [latest_poll1_version.content.pk, latest_poll2_version.content.pk],
            transform=lambda x: x.pk,
            ordered=False,
        )

    def test_queryset_filter_for_distinct_groupers(self):
        poll1_archived_version = PollVersionFactory(
            content__poll=self.initial_version.content.poll, state=ARCHIVED
        )
        poll1_published_version = PollVersionFactory(
            content__poll=self.initial_version.content.poll, state=PUBLISHED
        )
        poll2_version = PollVersionFactory()
        PollVersionFactory(content__poll=poll2_version.content.poll, state=ARCHIVED)
        poll2_archived_version = PollVersionFactory(
            content__poll=poll2_version.content.poll, state=ARCHIVED
        )

        versionable = VersionableItem(
            content_model=PollContent,
            grouper_field_name="poll",
            copy_function=default_copy,
        )

        qs_published_filter = {"versions__state__in": [PUBLISHED]}
        # Should be one published version
        self.assertQuerysetEqual(
            versionable.distinct_groupers(**qs_published_filter),
            [poll1_published_version.content.pk],
            transform=lambda x: x.pk,
            ordered=False,
        )

        qs_archive_filter = {"versions__state__in": [ARCHIVED]}
        # Should be two archived versions
        self.assertQuerysetEqual(
            versionable.distinct_groupers(**qs_archive_filter),
            [poll1_archived_version.content.pk, poll2_archived_version.content.pk],
            transform=lambda x: x.pk,
            ordered=False,
        )

    def test_for_grouper(self):
        poll1_version2 = PollVersionFactory(
            content__poll=self.initial_version.content.poll
        )
        poll2_version = PollVersionFactory()
        PollVersionFactory(content__poll=poll2_version.content.poll)
        PollVersionFactory(content__poll=poll2_version.content.poll)

        versionable = VersionableItem(
            content_model=PollContent,
            grouper_field_name="poll",
            copy_function=default_copy,
        )

        self.assertQuerysetEqual(
            versionable.for_grouper(self.initial_version.content.poll),
            [self.initial_version.content.pk, poll1_version2.content.pk],
            transform=lambda x: x.pk,
            ordered=False,
        )

    def test_grouper_model(self):
        versionable = VersionableItem(
            content_model=PollContent,
            grouper_field_name="poll",
            copy_function=default_copy,
        )

        self.assertEqual(versionable.grouper_model, Poll)

    def test_content_model_is_sideframe_editable_for_sideframe_disabled_model(self):
        """
        A content model with placeholders should not be opened in the sideframe
        """
        versionable = VersionableItem(
            content_model=PageContent,
            grouper_field_name="page",
            copy_function=default_copy,
        )

        self.assertEqual(versionable.content_model_is_sideframe_editable, False)

    def test_content_model_is_sideframe_editable_for_sideframe_enabled_model(self):
        """
        A content model without placeholders should be opened in the sideframe
        """
        versionable = VersionableItem(
            content_model=PollContent,
            grouper_field_name="poll",
            copy_function=default_copy,
        )

        self.assertEqual(versionable.content_model_is_sideframe_editable, True)


class VersionableItemProxyModelTestCase(CMSTestCase):
    @classmethod
    def setUpClass(cls):
        cls._all_models = copy.deepcopy(apps.all_models)

    @classmethod
    def tearDownClass(cls):
        apps.all_models = cls._all_models

    def tearDown(self):
        apps.all_models.pop("djangocms_versioning", None)

    def test_version_model_proxy(self):
        versionable = VersionableItem(
            content_model=PersonContent,
            grouper_field_name="person",
            copy_function=default_copy,
        )
        version_model_proxy = versionable.version_model_proxy

        self.assertIn(Version, version_model_proxy.mro())
        self.assertEqual(version_model_proxy.__name__, "PersonContentVersion")
        self.assertEqual(version_model_proxy._source_model, PersonContent)
        self.assertTrue(version_model_proxy._meta.proxy)

    def test_version_model_proxy_cached(self):
        """Test that version_model_proxy property is cached
        and return value is created once."""
        versionable = VersionableItem(
            content_model=PersonContent,
            grouper_field_name="person",
            copy_function=default_copy,
        )

        self.assertEqual(
            id(versionable.version_model_proxy), id(versionable.version_model_proxy)
        )


class DefaultCopyTestCase(CMSTestCase):
    def setUp(self) -> None:
        self.fancy_poll = FancyPoll(
            template="mytemplate-to-be-copied.html"
        )
        self.fancy_poll.save()
        placeholder = Placeholder(slot="copythis", default_width=3141592653589323)
        placeholder.save()
        self.plugins = [Text(
                body=f"plugin text {i+1}",
                position=i+1,
                language="en",
                placeholder=placeholder,
                plugin_type="SimpleTextPlugin",
            ) for i in range(3)]

        for plugin in self.plugins:
            placeholder.add_plugin(plugin)

        self.fancy_poll.placeholders.add(placeholder, Placeholder(slot="second placeholder"), bulk=False)

    def tearDown(self) -> None:
        self.fancy_poll.delete()

    def test_default_copy(self):
        # Since FancyPoll is not Versioned we have to give it its own _original_manager
        FancyPoll._original_manager = FancyPoll.objects
        # Use default_copy
        copy = default_copy(self.fancy_poll)

        self.assertIsNotNone(copy.pk)  # saved?

        self.assertNotEqual(copy.pk, self.fancy_poll.pk)  # Not the same object
        self.assertEqual(copy.template, self.fancy_poll.template)  # but the same content

        copied_placeholders = copy.placeholders.all()
        # One placeholder?
        self.assertEqual(len(copied_placeholders), 2)
        copied_placeholder = copied_placeholders.filter(slot="copythis").first()
        # Placeholder copied?
        self.assertEqual(copied_placeholder.default_width, 3141592653589323)
        # Is it actually a new placeholder?
        self.assertNotEqual(copied_placeholder.pk, self.fancy_poll.placeholders.first().pk)

        copied_plugins = Text.objects.filter(placeholder=copied_placeholder)
        # All plugins?
        self.assertEqual(len(copied_plugins), len(self.plugins))
        # Correctly copied
        for old, new in zip(copied_plugins, self.plugins):
            self.assertNotEqual(old.pk, new.pk)  # Different pk
            self.assertEqual(old.body, new.body)  # Same content

