from wheel import Wheel, Pocket
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Outcome:
    name: str
    odds: int

    def __str__(self):
        return f"{self.name} ({self.odds}:1)"


class TableLimit(object):
    def __init__(self, min=1, max=None):
        self.min = min
        self.max = max

    def __str__(self):
        return "[{0}:{1}]".format(self.min, self.max)


class Table(object):
    def __init__(self, wheel: Wheel, limits=None, bets=None):
        self.wheel = wheel
        self.pockets = tuple(Pocket() for _ in self.wheel.get_track())
        self.limits = self.get_defaults().copy()
        self.limits.update({k: TableLimit(**v) for k, v in limits.items()} if limits else {})
        self.outcomes = {}
        self.winner = None

        build_pockets(self)
        self.bets = []
        if bets:
            # Standard Bets
            self.bets += [Bet(table=self, **bet) for bet in bets if
                          not (re.match(Bet.NeighborsRegEx, bet['type']) or bet['type'] == 'sector')] if bets else {}

            # Neighbors Bets
            neighbors_bets = [Bet.from_neighbors(table=self, **bet) for bet in bets if
                              re.match(Bet.NeighborsRegEx, bet['type'])]
            self.bets += [inner for outer in neighbors_bets for inner in outer]

            # Sector Bets
            sector_bets = [Bet.from_sector(table=self, **bet) for bet in bets if bet['type'] == 'sector']
            self.bets += [inner for outer in sector_bets for inner in outer]

            inside_wager = sum([bet.wager for bet in self.bets if bet.type not in ["column", "dozen", "outside"]])

            if inside_wager and inside_wager < self.limits["totalInside"].min:
                raise InsideBetsTooSmall(inside_wager, self.limits["totalInside"].min)
            if self.limits["totalInside"].max and inside_wager > self.limits["totalInside"].max:
                raise InsideBetsTooLarge(inside_wager, self.limits["totalInside"].max)

    @staticmethod
    def get_defaults():
        return {
            "straightUp":   TableLimit(min=1, max=None),
            "split":        TableLimit(min=1, max=None),
            "split3":       TableLimit(min=1, max=None),
            "street":       TableLimit(min=1, max=None),
            "corner":       TableLimit(min=1, max=None),
            "first4":       TableLimit(min=1, max=None),
            "first5":       TableLimit(min=1, max=None),
            "doubleStreet": TableLimit(min=1, max=None),
            "column":       TableLimit(min=1, max=None),
            "dozen":        TableLimit(min=1, max=None),
            "outside":      TableLimit(min=1, max=None),
            "totalInside":  TableLimit(min=1, max=None),
        }

    def add_outcome(self, number: int, outcome: Outcome):
        pockets = list(self.pockets)
        pocket = set(pockets[number])
        pocket.add(outcome)
        pockets[number] = Pocket(pocket)
        self.pockets = tuple(pockets)
        if outcome.name in self.outcomes and self.outcomes[outcome.name] != outcome:
            raise ValueError(f"Duplicate Outcome Name Found: {outcome.name}")
        else:
            self.outcomes[outcome.name] = outcome

    def get_outcome(self, name: str):
        return self.outcomes.get(name)

    def get_outcome_by_type_location(self, type: str, location):
        if type == "straightUp":
            return self.get_outcome(str(location) if
                                    (isinstance(location, int) or isinstance(location, str)) else str(location.pop()))
        elif type == "outside":
            return self.get_outcome(location.capitalize())
        elif type in ['first4', 'first5']:
            return self.get_outcome('Zero-Line')
        elif type == 'split3':
            search_key = '3Way'
        elif type in ["split", "street", "corner", "line", "column", "dozen"]:
            search_key = type.capitalize()
        else:
            raise UnableToDetermineBet(type=type, location=location)
        # secondPass = [val for key, val in firstPass.items() if location & ]
        pocket_numbers = list(map(lambda x: 37 if x == '00' else int(x), location))
        pockets = list({val for key, val in enumerate(self.pockets) if key in pocket_numbers})
        if len(pockets) != len(location):
            missing = set(map(lambda x: '00' if x == 37 else x, pocket_numbers)) - set(range(0, len(self.pockets)))
            raise Exception("Location Not Found: {0}".format(missing))
        outcomes = pockets[0].intersection(*pockets)
        filtered_outcomes = {val for val in outcomes if search_key in val.name}
        if len(filtered_outcomes) == 1:
            return list(filtered_outcomes)[0]
        raise UnableToDetermineBet(type, location, filtered_outcomes)

    def choose(self, hash):
        # Transform first 13 characters of hash into decimal (max: 9223372036854775807)
        h = int(hash[0:13], 16)
        pocket_count = len(self.pockets)
        res = h % pocket_count
        self.winner = {
            'location': ('00' if res == 37 else res),
            'color':    ('Green' if res in [0, 37] else (
                'Red' if res in Wheel.get_red() else 'Black')),
            'parity':   (None if res in [0, 37] else ('Odd' if res % 2 else 'Even')),
        }
        return self.pockets[res]


def add_zero_line(table: Table):
    # Zero Line Bet
    odds = 6 if table.wheel == Wheel.AMERICAN else 8
    zero = Outcome("Zero-Line", odds)
    table.add_outcome(0, zero)
    table.add_outcome(1, zero)
    table.add_outcome(2, zero)
    table.add_outcome(3, zero)
    if table.wheel == Wheel.AMERICAN:
        table.add_outcome(37, zero)


def add_even_money(table: Table):
    # Even-Money Bets
    red = Outcome('Red', 1)
    black = Outcome('Black', 1)
    even = Outcome('Even', 1)
    odd = Outcome('Odd', 1)
    high = Outcome('High', 1)
    low = Outcome('Low', 1)
    for n in range(1, 37):
        if n < 19:
            table.add_outcome(n, low)
        else:
            table.add_outcome(n, high)

        if n % 2 == 0:
            table.add_outcome(n, even)
        else:
            table.add_outcome(n, odd)

        if n in Wheel.get_red():
            table.add_outcome(n, red)
        else:
            table.add_outcome(n, black)


def add_column(table: Table):
    # Column Bets
    for c in range(0, 3):
        column = Outcome(f"Column {c + 1}", 2)
        for r in range(0, 12):
            table.add_outcome(3 * r + c + 1, column)


def add_dozen(table: Table):
    # Dozen Bets
    for d in range(0, 3):
        dozen = Outcome(f"Dozen {d + 1}", 2)
        for m in range(0, 12):
            table.add_outcome(12 * d + m + 1, dozen)


def add_line(table: Table):
    # Line Bets
    for r in range(0, 11):
        n = 3 * r + 1
        line = Outcome(f"Line {n + 1}", 8)
        table.add_outcome(n, line)
        table.add_outcome(n + 1, line)
        table.add_outcome(n + 2, line)
        table.add_outcome(n + 3, line)
        table.add_outcome(n + 4, line)
        table.add_outcome(n + 5, line)


def add_corner(table: Table):
    # Corner Bets
    for r in range(0, 11):
        n = 3 * r + 1
        corner = Outcome(f"Corner {n}-{n + 1}-{n + 3}-{n + 4}", 8)
        table.add_outcome(n, corner)
        table.add_outcome(n + 1, corner)
        table.add_outcome(n + 3, corner)
        table.add_outcome(n + 4, corner)
        n = 3 * r + 2
        corner = Outcome(f"Corner {n}-{n + 1}-{n + 3}-{n + 4}", 8)
        table.add_outcome(n, corner)
        table.add_outcome(n + 1, corner)
        table.add_outcome(n + 3, corner)
        table.add_outcome(n + 4, corner)


def add_street(table: Table):
    # Street Bets
    for r in range(0, 12):
        n = 3 * r + 1
        street = Outcome(f"Street {r + 1}", 11)
        table.add_outcome(n, street)
        table.add_outcome(n + 1, street)
        table.add_outcome(n + 2, street)


def add_split3(table: Table):
    # Split3 Bets

    z12 = Outcome('3Way 0-1-2', 11)
    table.add_outcome(0, z12)
    table.add_outcome(1, z12)
    table.add_outcome(2, z12)
    if table.wheel == Wheel.AMERICAN:
        zy2 = Outcome('3Way 0-00-2', 11)
        table.add_outcome(0, zy2)
        table.add_outcome(37, zy2)
        table.add_outcome(2, zy2)
        y23 = Outcome('3Way 00-2-3', 11)
        table.add_outcome(3, y23)
        table.add_outcome(37, y23)
        table.add_outcome(2, y23)
    else:
        z23 = Outcome('3Way 0-2-3', 11)
        table.add_outcome(0, z23)
        table.add_outcome(3, z23)
        table.add_outcome(2, z23)


def add_split(table: Table):
    # Split Bets
    for r in range(0, 12):
        n = 3 * r + 1
        split = Outcome(f"Split {n}-{n + 1}", 17)
        table.add_outcome(n, split)
        table.add_outcome(n + 1, split)
        n = 3 * r + 2
        split = Outcome(f"Split {n}-{n + 1}", 17)
        table.add_outcome(n, split)
        table.add_outcome(n + 1, split)
    for n in range(1, 34):
        split = Outcome(f"Split {n}-{n + 3}", 17)
        table.add_outcome(n, split)
        table.add_outcome(n + 3, split)
    z1 = Outcome('Split 0-1', 17)
    table.add_outcome(0, z1)
    table.add_outcome(1, z1)
    if table.wheel == Wheel.AMERICAN:
        y3 = Outcome('Split 00-3', 17)
        table.add_outcome(3, y3)
        table.add_outcome(37, y3)
        yz = Outcome('Split 0-00', 17)
        table.add_outcome(0, yz)
        table.add_outcome(37, yz)
    else:
        z2 = Outcome('Split 0-2', 17)
        table.add_outcome(0, z2)
        table.add_outcome(2, z2)
        z3 = Outcome('Split 0-3', 17)
        table.add_outcome(0, z3)
        table.add_outcome(3, z3)


def add_straight(table: Table):
    # Straight Bets
    for n in range(0, 37):
        table.add_outcome(n, Outcome(str(n), 35))
    if table.wheel == Wheel.AMERICAN:
        table.add_outcome(37, Outcome('00', 35))


def build_pockets(table: Table):
    add_straight(table=table)
    add_split(table=table)
    add_split3(table=table)
    add_street(table=table)
    add_corner(table=table)
    add_line(table=table)
    add_dozen(table=table)
    add_column(table=table)
    add_even_money(table=table)
    add_zero_line(table=table)


class BadBetException(Exception):
    pass


class BetNotAvailable(BadBetException):
    pass


class BetTooSmallException(BadBetException):
    def __init__(self, bet, minimum):
        self.bet = bet
        self.minimum = minimum


class BetTooLargeException(BadBetException):
    def __init__(self, bet, maximum):
        self.bet = bet
        self.maximum = maximum


class InsideBetsTooSmall(BadBetException):
    def __init__(self, total, minimum):
        self.total = total
        self.minimum = minimum


class InsideBetsTooLarge(BadBetException):
    def __init__(self, total, maximum):
        self.total = total
        self.maximum = maximum


class UnableToDetermineBet(BadBetException):
    def __init__(self, type, location, found=None):
        self.type = type
        self.location = location
        self.found = found


class Bet(object):
    NeighborsRegEx: str = '^neighbors([1-9])$'

    @classmethod
    def from_neighbors(cls, table: Table, type, location, wager):
        match = re.match(cls.NeighborsRegEx, type.lower())
        if not match:
            raise UnableToDetermineBet(type=type, location=location)
        num_neighbors_per_side = int(match.group(1))
        total_bets = num_neighbors_per_side * 2 + 1
        if wager % total_bets:
            raise BadBetException('Wager for $0 should be multiple of $2'.format(type, total_bets))
        if isinstance(location, list):
            if len(location) != 1:
                raise UnableToDetermineBet(type=type, location=location)
            location = location[0]
        location = 37 if location == '00' else location
        if isinstance(location, str) and location.isnumeric():
            location = int(location)
        track = table.wheel.get_track()
        if location not in track:
            raise UnableToDetermineBet(type=type, location=location)
        track_index = track.index(location)
        pockets = [track[i] for i in
                   range(track_index - num_neighbors_per_side, track_index + num_neighbors_per_side + 1)]
        return [cls(table, 'straightUp', [pocket], wager / total_bets) for pocket in pockets]

    @classmethod
    def from_sector(cls, table: Table, type, location, wager):
        if table.wheel != Wheel.EUROPEAN:
            raise BetNotAvailable
        location = location.lower()
        if location == "jeu zero":
            return cls.from_sector_jeu_zero(table=table, wager=wager)
        if 'tiers' in location:
            return cls.from_sector_tiers(table=table, wager=wager)
        if 'voisins' in location:
            return cls.from_sector_voisins(table=table, wager=wager)
        if 'orphelins' in location:
            return cls.from_sector_orphelins(table=table, location=location, wager=wager)
        raise UnableToDetermineBet(type=type, location=location)

    @classmethod
    def from_sector_tiers(cls, table: Table, wager):
        if table.wheel != Wheel.EUROPEAN:
            raise BetNotAvailable
        if wager % 6:
            raise BadBetException('Wager for sector Tiers du Cylindre should be multiple of 6')
        return [
            Bet(table=table, type='split', location=[5, 8], wager=(wager / 6)),
            Bet(table=table, type='split', location=[10, 11], wager=(wager / 6)),
            Bet(table=table, type='split', location=[13, 16], wager=(wager / 6)),
            Bet(table=table, type='split', location=[23, 24], wager=(wager / 6)),
            Bet(table=table, type='split', location=[27, 30], wager=(wager / 6)),
            Bet(table=table, type='split', location=[33, 36], wager=(wager / 6)),
        ]

    @classmethod
    def from_sector_voisins(cls, table: Table, wager):
        if table.wheel != Wheel.EUROPEAN:
            raise BetNotAvailable
        if wager % 9:
            raise BadBetException('Wager for sector les Voisins du Zero should be multiple of 9')
        return [
            Bet(table=table, type='split', location=[4, 7], wager=(wager / 9)),
            Bet(table=table, type='split', location=[12, 15], wager=(wager / 9)),
            Bet(table=table, type='split', location=[18, 21], wager=(wager / 9)),
            Bet(table=table, type='split', location=[19, 22], wager=(wager / 9)),
            Bet(table=table, type='split', location=[32, 35], wager=(wager / 9)),
            Bet(table=table, type='split3', location=[0, 2, 3], wager=(2 * wager / 9)),
            Bet(table=table, type='corner', location=[25, 26, 28, 29], wager=(2 * wager / 9)),
        ]

    @classmethod
    def from_sector_orphelins(cls, table: Table, location, wager):
        if table.wheel != Wheel.EUROPEAN:
            raise BetNotAvailable
        if 'plein' in location.lower():
            if wager % 8:
                raise BadBetException('Wager for sector les Orphelins en Plein should be multiple of 8')
            return [
                Bet(table=table, type='straightUp', location=1, wager=(wager / 8)),
                Bet(table=table, type='straightUp', location=6, wager=(wager / 8)),
                Bet(table=table, type='straightUp', location=9, wager=(wager / 8)),
                Bet(table=table, type='straightUp', location=14, wager=(wager / 8)),
                Bet(table=table, type='straightUp', location=17, wager=(wager / 8)),
                Bet(table=table, type='straightUp', location=20, wager=(wager / 8)),
                Bet(table=table, type='straightUp', location=31, wager=(wager / 8)),
                Bet(table=table, type='straightUp', location=34, wager=(wager / 8)),
            ]
        if wager % 5:
            raise BadBetException('Wager for sector les Orphelins en Cheval should be multiple of 5')
        return [
            Bet(table=table, type='split', location=[6, 9], wager=(wager / 5)),
            Bet(table=table, type='split', location=[14, 17], wager=(wager / 5)),
            Bet(table=table, type='split', location=[17, 20], wager=(wager / 5)),
            Bet(table=table, type='split', location=[31, 34], wager=(wager / 5)),
            Bet(table=table, type='straightUp', location=1, wager=(wager / 5)),
        ]

    @classmethod
    def from_sector_jeu_zero(cls, table: Table, wager):
        if table.wheel != Wheel.EUROPEAN:
            raise BetNotAvailable
        if wager % 4:
            raise BadBetException('Wager for sector Jeu Zero should be multiple of 4')
        return [
            Bet(table=table, type='split', location=[0, 3], wager=(wager / 4)),
            Bet(table=table, type='split', location=[12, 15], wager=(wager / 4)),
            Bet(table=table, type='split', location=[32, 35], wager=(wager / 4)),
            Bet(table=table, type='straightUp', location=26, wager=(wager / 4)),
        ]

    def __init__(self, table: Table, type, location, wager=1):
        self.win = None
        self.type = type
        self.location = location
        self.wager = wager
        self.outcome = table.get_outcome_by_type_location(type=type, location=location)
        if wager < table.limits[type].min:
            raise BetTooSmallException(self, table.limits[type].min)
        if table.limits[type].max and wager > table.limits[type].max:
            raise BetTooLargeException(self, table.limits[type].max)

    def __str__(self):
        return "{0} Bet for {1} at {2}".format(self.type, self.wager, self.location)

    def __repr__(self):
        return "Bet(type={0},location={1},wager={2})".format(self.type, self.location, self.wager)
