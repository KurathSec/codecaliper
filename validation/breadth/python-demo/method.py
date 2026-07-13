def settle(orders, ledger):
	for o in orders:
		if o.status == "open":
			if o.amount > ledger.limit:
				ledger.flag(o)
			else:
				ledger.apply(o)
	return ledger.balance()
