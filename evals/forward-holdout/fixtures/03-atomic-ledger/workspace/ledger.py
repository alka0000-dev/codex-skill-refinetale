class Overdraft(Exception):
    pass


class Ledger:
    def __init__(self, balances=None):
        self.balances = dict(balances or {})
        self.audit = []

    def apply(self, account, delta):
        balance = self.balances.get(account, 0) + delta
        if balance < 0:
            raise Overdraft(account)
        self.balances[account] = balance
        self.audit.append((account, delta, balance))
        return balance
