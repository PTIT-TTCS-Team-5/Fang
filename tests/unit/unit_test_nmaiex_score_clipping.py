import unittest
from unittest.mock import patch

from app.core.nmaiex_config import nmaiex_settings
from app.services.nmaiex_ranking_service import clip_score


class NMAIexScoreClippingTests(unittest.TestCase):
    def test_score_is_raw_by_default(self):
        with patch.object(nmaiex_settings, "nmaiex_enable_score_clip", False):
            self.assertEqual(clip_score(1.25), 1.25)
            self.assertEqual(clip_score(-0.4), -0.4)

    def test_score_can_be_clipped_for_legacy_display(self):
        with patch.object(nmaiex_settings, "nmaiex_enable_score_clip", True):
            self.assertEqual(clip_score(1.25), 1.0)
            self.assertEqual(clip_score(-0.4), 0.0)
            self.assertEqual(clip_score(0.7), 0.7)


if __name__ == "__main__":
    unittest.main()
