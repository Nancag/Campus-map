import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.geo import haversine_km, within_radius


class TestGeo(unittest.TestCase):
    def test_same_point_zero(self):
        self.assertEqual(haversine_km(25.44, 119.62, 25.44, 119.62), 0)

    def test_known_distance_between_campuses(self):
        d = haversine_km(25.44, 119.62, 25.86, 119.51)
        self.assertTrue(40 < d < 60)

    def test_within_radius_true(self):
        self.assertTrue(within_radius(25.44, 119.62, 25.45, 119.63, 40))

    def test_within_radius_false(self):
        self.assertFalse(within_radius(25.44, 119.62, 30.0, 120.0, 40))

    def test_invalid_latitude_raises(self):
        with self.assertRaises(ValueError):
            haversine_km(91, 119.62, 25.44, 119.62)

    def test_invalid_longitude_raises(self):
        with self.assertRaises(ValueError):
            haversine_km(25.44, 181, 25.44, 119.62)

    def test_invalid_type_raises(self):
        with self.assertRaises(ValueError):
            haversine_km("x", 119.62, 25.44, 119.62)


if __name__ == "__main__":
    unittest.main()