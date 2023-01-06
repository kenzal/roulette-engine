from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
from typing import List
import numpy as np
import json
import jsonschema
import math
import re
import secrets

dictfilt = lambda x, y: dict([ (i,x[i]) for i in x if i in set(y) ])

schemaFile = open('json-schema/RouletteRequestSchema.json');
requestSchema = json.load(schemaFile)


class WheelType(Enum):
    AMERICAN = 'American'
    EUROPEAN = 'European'


@dataclass(frozen=True)
class Outcome:
    name: str
    odds: int

    def __str__(self):
        return f"{self.name} ({self.odds}:1)"

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

class UnableToDeterminBet(BadBetException):
    def __init__(self, type, location, found=None):
        self.type = type
        self.location = location
        self.found = found

class Bet(object):
    NeighborsRegEx = '^neighbors([1-9])$'
    def winAmount(self):
        return self.amountBet * self.outcome.odds + self.amountBet

    def loseAmount(self):
        return self.amountBet
    @classmethod
    def fromNeighbors(cls, engine:'RouletteEngine', type, location, wager):
        match = re.match(cls.NeighborsRegEx, type.lower())
        if not match:
            raise UnableToDeterminBet(type=type, location=location)
        numNeighborsPerSide = int(match.group(1))
        totalBets = numNeighborsPerSide*2+1
        if wager % totalBets:
            raise BadBetException('Wager for $0 should be multiple of $2'.format(type, totalBets))
        if isinstance(location, list):
            if len(location) != 1:
                raise UnableToDeterminBet(type=type, location=location)
            location = location[0]
        location = 37 if location == '00' else location
        if isinstance(location, str) and location.isnumeric():
            location = int(location)
        track = engine.getTrack()
        if location not in track:
            raise UnableToDeterminBet(type=type, location=location)
        bets = {}
        trackIndex = track.index(location)
        pockets = [track[i] for i in range(trackIndex-numNeighborsPerSide, trackIndex+numNeighborsPerSide+1)]
        return [cls(engine, 'straightUp', [pocket], wager/totalBets) for pocket in pockets]
    @classmethod
    def fromSector(cls, engine:'RouletteEngine', type, location, wager):
        if engine.wheel != WheelType.EUROPEAN:
            raise BetNotAvailable
        location = location.lower()
        if location=="jeu zero":
            return cls.fromSectorJeuZero(engine=engine, type=type, location=location, wager=wager)
        if 'tiers' in location:
            return cls.fromSectorTiers(engine=engine, type=type, location=location, wager=wager)
        if 'voisins' in location:
            return cls.fromSectorVoisins(engine=engine, type=type, location=location, wager=wager)
        if 'orphelins' in location:
            return cls.fromSectorOrphelins(engine=engine, type=type, location=location, wager=wager)
        raise UnableToDeterminBet(type=type, location=location)
    @classmethod
    def fromSectorTiers(cls, engine:'RouletteEngine', type, location, wager):
        if engine.wheel != WheelType.EUROPEAN:
            raise BetNotAvailable
        if wager % 6:
            raise BadBetException('Wager for sector Tiers du Cylindre should be multiple of 6')     
        return [
            Bet(engine=engine, type='split', location=[ 5, 8], wager=(wager/6)),
            Bet(engine=engine, type='split', location=[10,11], wager=(wager/6)),
            Bet(engine=engine, type='split', location=[13,16], wager=(wager/6)),
            Bet(engine=engine, type='split', location=[23,24], wager=(wager/6)),
            Bet(engine=engine, type='split', location=[27,30], wager=(wager/6)),
            Bet(engine=engine, type='split', location=[33,36], wager=(wager/6)),
            ]
    @classmethod
    def fromSectorVoisins(cls, engine:'RouletteEngine', type, location, wager):
        if engine.wheel != WheelType.EUROPEAN:
            raise BetNotAvailable
        if wager % 9:
            raise BadBetException('Wager for sector les Voisins du Zero should be multiple of 9')     
        return [
            Bet(engine=engine, type='split',  location=[ 4, 7],       wager=(  wager/9)),
            Bet(engine=engine, type='split',  location=[12,15],       wager=(  wager/9)),
            Bet(engine=engine, type='split',  location=[18,21],       wager=(  wager/9)),
            Bet(engine=engine, type='split',  location=[19,22],       wager=(  wager/9)),
            Bet(engine=engine, type='split',  location=[32,35],       wager=(  wager/9)),
            Bet(engine=engine, type='split3', location=[ 0, 2, 3],    wager=(2*wager/9)),
            Bet(engine=engine, type='corner', location=[25,26,28,29], wager=(2*wager/9)),
        ]
    @classmethod
    def fromSectorOrphelins(cls, engine:'RouletteEngine', type, location, wager):
        if engine.wheel != WheelType.EUROPEAN:
            raise BetNotAvailable
        if 'plein' in location.lower():
            if wager % 8:
                raise BadBetException('Wager for sector les Orphelins en Plein should be multiple of 8')
            return [
                Bet(engine=engine, type='straightUp', location= 1, wager=(wager/8)),
                Bet(engine=engine, type='straightUp', location= 6, wager=(wager/8)),
                Bet(engine=engine, type='straightUp', location= 9, wager=(wager/8)),
                Bet(engine=engine, type='straightUp', location=14, wager=(wager/8)),
                Bet(engine=engine, type='straightUp', location=17, wager=(wager/8)),
                Bet(engine=engine, type='straightUp', location=20, wager=(wager/8)),
                Bet(engine=engine, type='straightUp', location=31, wager=(wager/8)),
                Bet(engine=engine, type='straightUp', location=34, wager=(wager/8)),
            ]
        if wager % 5:
            raise BadBetException('Wager for sector les Orphelins en Cheval should be multiple of 5')      
        return [
            Bet(engine=engine, type='split',      location=[ 6, 9], wager=(wager/5)),
            Bet(engine=engine, type='split',      location=[14,17], wager=(wager/5)),
            Bet(engine=engine, type='split',      location=[17,20], wager=(wager/5)),
            Bet(engine=engine, type='split',      location=[31,34], wager=(wager/5)),
            Bet(engine=engine, type='straightUp', location=1,       wager=(wager/5)),
        ]
    @classmethod
    def fromSectorJeuZero(cls, engine:'RouletteEngine', type, location, wager):
        if engine.wheel != WheelType.EUROPEAN:
            raise BetNotAvailable
        if wager % 4:
            raise BadBetException('Wager for sector Jeu Zero should be multiple of 4')      
        return [
            Bet(engine=engine, type='split',      location=[ 0, 3], wager=(wager/4)),
            Bet(engine=engine, type='split',      location=[12,15], wager=(wager/4)),
            Bet(engine=engine, type='split',      location=[32,35], wager=(wager/4)),
            Bet(engine=engine, type='straightUp', location=26,      wager=(wager/4)),
        ]
    def __str__(self):
        return f"{self.amountBet} on {self.outcome}"
    def __init__(self, engine:'RouletteEngine', type, location, wager=1):
        self.type     = type
        self.location = location
        self.wager    = wager
        self.outcome  = engine.getOutcomeByTypeLocation(type=type, location=location)
        if wager < engine.table[type].min:
            raise BetTooSmallException(self, engine.table[type].min)
        if engine.table[type].max and wager > engine.table[type].max:
            raise BetTooLargeException(self, engine.table[type].max)
    def __str__(self):
        return "{0} Bet for {1} at {2}".format(self.type, self.wager, self.location)
    def __repr__(self):
        return "Bet(type={0},location={1},wager={2})".format(self.type, self.location, self.wager)

class TableLimit(object):
    def __init__(self, min=1, max=None):
        self.min = min
        self.max = max
    def __str__(self):
        return "[{0}:{1}]".format(self.min, self.max)
    def __repr__(self):
        return "TableLimit(min={0},max={1})".format(self.min, self.max)


class Pocket(frozenset):
    pass


class RouletteEngine(object):
    def __repr__(self):
        return "RouletteEngine(hash={0},wheel={1},table={2},bets={3})".format(self.hash, self.wheel, self.table if self.table!=self.defaultTable else None,self.bets if len(self.bets) else None)
    def __init__(self, hash=None, wheel: WheelType=WheelType.EUROPEAN, table=None, bets=None):
        hash = hash if hash else secrets.token_hex(32) 
        self.wheel = WheelType(wheel)
        self.pockets = tuple(Pocket() for i in range(38 if self.wheel==WheelType.AMERICAN else 37))
        self.hash = hash.lower()
        self.outcomes = {}
        self.defaultTable = {
            "straightUp":TableLimit(),
            "split":TableLimit(),
            "split3":TableLimit(),
            "street":TableLimit(),
            "corner":TableLimit(),
            "first4": TableLimit(),
            "first5":TableLimit(),
            "doubleStreet":TableLimit(),
            "column":TableLimit(),
            "dozen": TableLimit(),
            "outside": TableLimit(),
            "totalInside": TableLimit(),
            }
        self.table = self.defaultTable.copy()
        self.table.update({k: TableLimit(**v) for k, v in table.items()} if table else {})
        builder = PocketBuilder()
        builder.buildPockets(self)
        #Standard Bets
        self.bets = [Bet(engine=self, **bet) for bet in bets if not (re.match(Bet.NeighborsRegEx, bet['type']) or bet['type']=='sector')] if bets else {}
        
        #Neighbors Bets
        neighborsBets = [Bet.fromNeighbors(engine=self, **bet) for bet in bets if re.match(Bet.NeighborsRegEx, bet['type'])]
        self.bets += [inner for outer in neighborsBets for inner in outer]

        #Sector Bets
        sectorBets = [Bet.fromSector(engine=self, **bet) for bet in bets if bet['type']=='sector']
        self.bets += [inner for outer in sectorBets for inner in outer]


        insideWager = sum([bet.wager for bet in self.bets if bet.type not in ["column","dozen","outside"]])

        if insideWager and insideWager < self.table["totalInside"].min:
            raise InsideBetsTooSmall(insideWager, self.table["totalInside"].min)
        if self.table["totalInside"].max and insideWager > self.table["totalInside"].max:
            raise InsideBetsTooLarge(insideWager, self.table["totalInside"].max)
    def addOutcome(self, number: int, outcome: Outcome):
        pockets = list(self.pockets)
        pocket = set(pockets[number])
        pocket.add(outcome)
        pockets[number] = Pocket(pocket)
        self.pockets = tuple(pockets)
        if outcome.name in self.outcomes and self.outcomes[outcome.name] != outcome:
            raise ValueError(f"Duplicate Outcome Name Found: {outcome.name}")
        else:
            self.outcomes[outcome.name] = outcome
    def getTrack(self):
        if self.wheel == WheelType.AMERICAN:
            return [0, 28, 9, 26, 30, 11, 7, 20, 32, 17, 5, 22, 34, 
                    15, 3, 24, 36, 13, 1, 37, 27, 10, 25, 29, 12, 8, 
                    19, 31, 18, 6, 21, 33, 16, 4, 23, 35, 14, 2]
        return [0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36, 
                11, 30, 8, 23, 10, 5, 24, 16, 33, 1, 20, 14, 31, 9, 
                22, 18, 29, 7, 28, 12, 35, 3, 26]
    def getOutcome(self, name: str):
        return self.outcomes.get(name)
    def getOutcomeByTypeLocation(self, type: str, location):
        if type == "straightUp":
            return self.getOutcome(str(location) if np.isscalar(location) else str(location[0]))
        elif type == "outside":
            return self.getOutcome(location.capitalize())
        elif type in ['first4', 'first5']:
            return self.getOutcome('Zero-Line')
        elif type == 'split3':
            searchKey = '3Way'
        elif type in ["split","street","corner","line","column","dozen"]:
            searchKey = type.capitalize()
        else:
            raise UnknownBet
        #secondPass = [val for key, val in firstPass.items() if location & ]
        pocketNumbers = list(map(lambda x: 37 if x=='00' else x, location))
        pockets = list({val for key, val in enumerate(self.pockets) if key in pocketNumbers})
        if len(pockets) != len(location):
            missing = set(map(lambda x: '00' if x==37 else x, pocketNumbers)) - set(range(0,len(self.pockets)))
            raise Exception("Location Not Found: {0}".format(missing))
        outcomes = pockets[0].intersection(*pockets)
        filterdOutcomes = {val for val in outcomes if searchKey in val.name}
        if len(filterdOutcomes) == 1:
            return list(filterdOutcomes)[0]
        raise UnableToDeterminBet(type, location, filterdOutcomes)
        


    def choose(self):
        #Transform first 13 characters of hash into decimal (max: 9223372036854775807)
        h = int(self.hash[0:13], 16)
        pocketCount = len(self.pockets)
        res = h % pocketCount
        self.winner = {
            'location': ('00' if res==37 else res),
            'color': ('Green' if res in [0,37] else ('Red' if res in [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36] else 'Black')),
            'parity': (None if res in [0,37] else ('Odd' if res%2 else 'Even')),
            }
        return self.pockets[res]
    def spin(self):
        winner = self.choose()
        for bet in list(self.bets):
            if bet.outcome in winner:
                bet.win = True
                bet.payout = bet.outcome.odds * bet.wager
            else:
                bet.win = False
                bet.payout = 0
        self.success=True
        self.wager = {
        'payout': sum(bet.payout for bet in self.bets),
        'onTable': sum(bet.wager for bet in self.bets if bet.win),
        'placed': sum(bet.wager for bet in self.bets),
        'lost': sum(bet.wager for bet in self.bets if not bet.win)
        }
        self.wager['delta'] = self.wager['payout']+self.wager['onTable']-self.wager['lost']
    def getResult(self):
        if not hasattr(self, 'success'):
            self.spin()
        return self.toJson()
    def getJsonDict(self):
        members = dictfilt(self.__dict__, {"bets", "hash", "table", "success","wheel","winner","wager"})
        additional = {
            'winningBets':list(bet for bet in self.bets if bet.win),
        }
        return {**members, **additional}
    def toJson(self):
        return json.dumps(self, default=lambda o: o.value if isinstance(o,Enum) else o.getJsonDict() if 'getJsonDict' in dir(o) and callable(getattr(o,'getJsonDict')) else o.__dict__, sort_keys=True)



class PocketBuilder:
    def buildPockets(self, engine: RouletteEngine):
        self.addStraight(engine)
        self.addSplit(engine)
        self.addSplit3(engine)
        self.addStreet(engine)
        self.addCorner(engine)
        self.addLine(engine)        
        self.addDozen(engine)
        self.addColumn(engine)
        self.addEvenMoney(engine)
        self.addZeroLine(engine)

    def addStraight(self, engine: RouletteEngine):
        # Straight Bets
        for n in range(0, 37):
            engine.addOutcome(n, Outcome(str(n), 35))
        if engine.wheel == WheelType.AMERICAN:
            engine.addOutcome(37, Outcome('00', 35))

    def addSplit(self, engine: RouletteEngine):
        # Split Bets
        for r in range(0, 12):
            n = 3*r+1
            split = Outcome(f"Split {n}-{n+1}", 17)
            engine.addOutcome(n, split)
            engine.addOutcome(n+1, split)
            n = 3*r+2
            split = Outcome(f"Split {n}-{n+1}", 17)
            engine.addOutcome(n, split)
            engine.addOutcome(n+1, split)
        for n in range(1, 34):
            split = Outcome(f"Split {n}-{n+3}", 17)
            engine.addOutcome(n, split)
            engine.addOutcome(n+3, split)
        z1 = Outcome('Split 0-1', 17)
        engine.addOutcome(0,  z1)
        engine.addOutcome(1,  z1)
        if engine.wheel==WheelType.AMERICAN:
            y3 = Outcome('Split 00-3', 17)
            engine.addOutcome(3,  y3)
            engine.addOutcome(37, y3)
            yz = Outcome('Split 0-00', 17)
            engine.addOutcome(0,  yz)
            engine.addOutcome(37, yz)
        else:
            z2 = Outcome('Split 0-2', 17)
            engine.addOutcome(0,  z2)
            engine.addOutcome(2,  z2)
            z3 = Outcome('Split 0-3', 17)
            engine.addOutcome(0,  z3)
            engine.addOutcome(3,  z3)

    def addSplit3(self, engine: RouletteEngine):
        # Split3 Bets

        z12 = Outcome('3Way 0-1-2', 11)
        engine.addOutcome(0,  z12)
        engine.addOutcome(1,  z12)
        engine.addOutcome(2,  z12)
        if engine.wheel==WheelType.AMERICAN:
            zy2 = Outcome('3Way 0-00-2', 11)
            engine.addOutcome(0,  zy2)
            engine.addOutcome(37, zy2)
            engine.addOutcome(2,  zy2)
            y23 = Outcome('3Way 00-2-3', 11)
            engine.addOutcome(3,  y23)
            engine.addOutcome(37, y23)
            engine.addOutcome(2,  y23)
        else:
            z23 = Outcome('3Way 0-2-3', 11)
            engine.addOutcome(0,  z23)
            engine.addOutcome(3,  z23)
            engine.addOutcome(2,  z23)

    def addStreet(self, engine: RouletteEngine):
        # Street Bets
        for r in range(0, 12):
            n = 3*r+1
            street = Outcome(f"Street {r+1}", 11)
            engine.addOutcome(n, street)
            engine.addOutcome(n+1, street)
            engine.addOutcome(n+2, street)

    def addCorner(self, engine: RouletteEngine):
        # Corner Bets
        for r in range(0, 11):
            n = 3*r+1
            corner = Outcome(f"Corner {n}-{n+1}-{n+3}-{n+4}", 8)
            engine.addOutcome(n, corner)
            engine.addOutcome(n+1, corner)
            engine.addOutcome(n+3, corner)
            engine.addOutcome(n+4, corner)
            n = 3*r+2
            corner = Outcome(f"Corner {n}-{n+1}-{n+3}-{n+4}", 8)
            engine.addOutcome(n, corner)
            engine.addOutcome(n+1, corner)
            engine.addOutcome(n+3, corner)
            engine.addOutcome(n+4, corner)

    def addLine(self, engine: RouletteEngine):
        # Line Bets
        for r in range(0, 11):
            n = 3*r+1
            line = Outcome(f"Line {n+1}", 8)
            engine.addOutcome(n, line)
            engine.addOutcome(n+1, line)
            engine.addOutcome(n+2, line)
            engine.addOutcome(n+3, line)
            engine.addOutcome(n+4, line)
            engine.addOutcome(n+5, line)

    def addDozen(self, engine: RouletteEngine):
        # Dozen Bets
        for d in range(0, 3):
            dozen = Outcome(f"Dozen {d+1}", 2)
            for m in range(0, 12):
                engine.addOutcome(12*d+m+1, dozen)

    def addColumn(self, engine: RouletteEngine):
        #Column Bets
        for c in range(0, 3):
            column = Outcome(f"Column {c+1}", 2)
            for r in range(0, 12):
                engine.addOutcome(3*r+c+1, column)

    def addEvenMoney(self, engine: RouletteEngine):
        #Even-Money Bets
        red   = Outcome('Red',   1)
        black = Outcome('Black', 1)
        even  = Outcome('Even',  1)
        odd   = Outcome('Odd',   1)
        high  = Outcome('High',  1)
        low   = Outcome('Low',   1)
        for n in range(1,37):
            if n < 19:
                engine.addOutcome(n, low)
            else:
                engine.addOutcome(n, high)

            if n%2 == 0:
                engine.addOutcome(n, even)
            else:
                engine.addOutcome(n, odd)

            if n in [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]:
                engine.addOutcome(n, red)
            else:
                engine.addOutcome(n, black)

    def addZeroLine(self, engine: RouletteEngine):
        #Zero Line Bet
        odds = 6 if engine.wheel==WheelType.AMERICAN else 8
        zero = Outcome("Zero-Line", odds)
        engine.addOutcome(0,  zero)
        engine.addOutcome(1,  zero)
        engine.addOutcome(2,  zero)
        engine.addOutcome(3,  zero)
        if engine.wheel==WheelType.AMERICAN:
            engine.addOutcome(37,  zero)

def processRequest(request):
    try:
        jsonschema.validate(instance=request, schema=requestSchema)
    except jsonschema.exceptions.ValidationError as e:
        return json.dumps({"success": False,"exception": {"type": str(type(e)),"message": str(e)}})
    try:
        engine = RouletteEngine(**request)
        return engine.getResult()
    except Exception as e:
        return json.dumps({"success": False,"exception": {"type": str(type(e)),"message": str(e)}})
