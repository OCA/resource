# Copyright 2026 Daniel Reis
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from datetime import datetime, timedelta, timezone

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestPresence(TransactionCase):
    """The presence map answers where a resource is, over a period."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.resource = cls.env["resource.resource"].create(
            {"name": "John", "resource_type": "user"}
        )
        cls.site_a = cls.env["res.partner"].create(
            {"name": "Site A", "is_resource_location": True}
        )
        cls.site_b = cls.env["res.partner"].create(
            {"name": "Site B", "is_resource_location": True}
        )
        cls.now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        cls.end = cls.now + timedelta(days=14)

    def _map(self, resource=None):
        resource = resource or self.resource
        return resource.get_locations_on_period(self.now, self.end)[resource.id]

    def test_no_lines_means_anywhere(self):
        """A resource without presence records is available anywhere."""
        self.assertEqual(self._map(), {})

    def test_open_line_covers_window(self):
        """An undated, unscheduled line covers the whole period."""
        self.env["resource.location.presence"].create(
            {"resource_id": self.resource.id, "location_id": self.site_a.id}
        )
        self.assertTrue(self._map()[self.site_a.id])

    def test_undated_line_never_covers_other_sites(self):
        """Presence at A says nothing about B."""
        self.env["resource.location.presence"].create(
            {"resource_id": self.resource.id, "location_id": self.site_a.id}
        )
        self.assertNotIn(self.site_b.id, self._map())

    def test_dated_line_clips_coverage(self):
        """A dated line covers only inside its start/end window."""
        start = (self.now + timedelta(days=5)).date()
        end = (self.now + timedelta(days=7)).date()
        self.env["resource.location.presence"].create(
            {
                "resource_id": self.resource.id,
                "location_id": self.site_a.id,
                "date_start": start,
                "date_end": end,
            }
        )
        intervals = list(self._map()[self.site_a.id])
        self.assertEqual(len(intervals), 1)
        self.assertEqual(intervals[0][0].date(), start)
        self.assertEqual(intervals[0][1].date(), end + timedelta(days=1))

    def test_past_line_covers_nothing(self):
        """A presence record that already ended gives no coverage."""
        self.env["resource.location.presence"].create(
            {
                "resource_id": self.resource.id,
                "location_id": self.site_a.id,
                "date_start": (self.now - timedelta(days=10)).date(),
                "date_end": (self.now - timedelta(days=1)).date(),
            }
        )
        self.assertFalse(self._map().get(self.site_a.id))

    def test_first_line_wins_overlap(self):
        """Overlapping lines: the lower-sequence line keeps its instants."""
        self.env["resource.location.presence"].create(
            {
                "resource_id": self.resource.id,
                "location_id": self.site_a.id,
                "date_start": (self.now + timedelta(days=2)).date(),
                "date_end": (self.now + timedelta(days=4)).date(),
                "sequence": 10,
            }
        )
        self.env["resource.location.presence"].create(
            {
                "resource_id": self.resource.id,
                "location_id": self.site_b.id,
                "date_start": (self.now + timedelta(days=3)).date(),
                "date_end": (self.now + timedelta(days=8)).date(),
                "sequence": 20,
            }
        )
        result = self._map()
        a_end = list(result[self.site_a.id])[0][1].date()
        b_start = list(result[self.site_b.id])[0][0].date()
        # A keeps its full window; B starts only where A left off
        self.assertEqual(b_start, a_end)
