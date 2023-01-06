from enum import Enum
import json
import jsonschema
import secrets
from wheel import Wheel as RouletteWheel
from table import Table as RouletteTable


class RouletteEngine(object):
    def __init__(self, hash=None, wheel: RouletteWheel = RouletteWheel.EUROPEAN, table=None, bets=None):
        hash = hash if hash else secrets.token_hex(32)
        self.wager = None
        self.winner = None
        self.success = None
        self.wheel = RouletteWheel(wheel)

        self.hash = hash.lower()
        self.table = RouletteTable(wheel=self.wheel, limits=table, bets=bets)

    def spin(self):
        winner = self.table.choose(self.hash)
        for bet in list(self.table.bets):
            if bet.outcome in winner:
                bet.win = True
                bet.payout = bet.outcome.odds * bet.wager
            else:
                bet.win = False
                bet.payout = 0
        self.success = True
        self.wager = {
            'payout':  sum(bet.payout for bet in self.table.bets),
            'onTable': sum(bet.wager for bet in self.table.bets if bet.win),
            'placed':  sum(bet.wager for bet in self.table.bets),
            'lost':    sum(bet.wager for bet in self.table.bets if not bet.win)
        }
        self.wager['delta'] = self.wager['payout'] + self.wager['onTable'] - self.wager['lost']

    def get_result(self):
        if not self.success:
            self.spin()
        return self.to_json()

    def get_json_dict(self):
        members = dict_filter(self.__dict__, {"hash", "success", "wager"})
        additional = {
            'bets': self.table.bets,
            'table': self.table.limits,
            'winner': self.table.winner,
            'wheel': self.table.wheel,
            'winningBets': list(bet for bet in self.table.bets if bet.win),
        }
        return {**members, **additional}

    def to_json(self):
        return json.dumps(self,
                          default=lambda o: o.value if isinstance(o, Enum) else
                          o.get_json_dict() if 'get_json_dict' in dir(o) and callable(getattr(o, 'get_json_dict')) else
                          o.__dict__, sort_keys=True)


def dict_filter(haystack, needles):
    return dict([(i, haystack[i]) for i in haystack if i in set(needles)])


schemaFile = open('RouletteRequestSchema.json')
requestSchema = json.load(schemaFile)


def process_request(request):
    try:
        jsonschema.validate(instance=request, schema=requestSchema)
    except jsonschema.exceptions.ValidationError as e:
        return json.dumps({"success": False, "exception": {"type": str(type(e)), "message": str(e)}})
    try:
        engine = RouletteEngine(**request)
        return engine.get_result()
    except Exception as e:
        return json.dumps({"success": False, "exception": {"type": str(type(e)), "message": str(e)}})
