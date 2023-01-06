from enum import Enum


class Pocket(frozenset):
    pass


class Wheel(Enum):
    AMERICAN = 'American'
    EUROPEAN = 'European'

    def get_track(self):
        if self == self.AMERICAN:
            return [0, 28, 9, 26, 30, 11, 7, 20, 32, 17, 5, 22, 34,
                    15, 3, 24, 36, 13, 1, 37, 27, 10, 25, 29, 12, 8,
                    19, 31, 18, 6, 21, 33, 16, 4, 23, 35, 14, 2]
        return [0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36,
                11, 30, 8, 23, 10, 5, 24, 16, 33, 1, 20, 14, 31, 9,
                22, 18, 29, 7, 28, 12, 35, 3, 26]

    @staticmethod
    def get_red():
        return [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]

    @staticmethod
    def get_black():
        return [2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35]

    def get_green(self):
        if self == self.AMERICAN:
            return [0, 37]
        return [0]
