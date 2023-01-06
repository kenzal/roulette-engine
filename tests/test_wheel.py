import unittest
from wheel import Wheel

def intersection(lst1, lst2):
    lst3 = [value for value in lst1 if value in lst2]
    return lst3

class TestWheelConsistency(unittest.TestCase):

    def test_values(self):
        self.assertEqual(Wheel.AMERICAN.value, 'American')
        self.assertEqual(Wheel.EUROPEAN.value, 'European')

    def test_track_count(self):
        self.assertEqual(len(Wheel.AMERICAN.get_track()), 38)
        self.assertEqual(len(Wheel.EUROPEAN.get_track()), 37)

    def test_track_string(self):
        for wheel in [Wheel.AMERICAN, Wheel.EUROPEAN]:
            self.assertEqual(len(wheel.get_track()), len(wheel.get_track_str()))
        self.assertIn('00', Wheel.AMERICAN.get_track_str())
        self.assertNotIn('00', Wheel.EUROPEAN.get_track_str())

    def test_colors_and_totals(self):
        self.assertEqual([], intersection(Wheel.get_red(), Wheel.get_black()))
        for wheel in [Wheel.AMERICAN, Wheel.EUROPEAN]:
            self.assertEqual(wheel.get_track().sort(),
                             intersection(
                                 intersection(wheel.get_red(), wheel.get_black()),
                                 wheel.get_green()).sort())
            self.assertEqual(wheel.get_track_str().sort(),
                             intersection(
                                 intersection(wheel.get_red_str(), wheel.get_black_str()),
                                 wheel.get_green_str()).sort())


if __name__ == '__main__':
    unittest.main()