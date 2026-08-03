// Tab-policy probe input: a valid compilation unit whose indentation is
// entirely tab characters, deep enough that the tab convention dominates the
// indentation features. run_audit.py derives the spaces-x8 and spaces-x1
// variants from this file mechanically; only this master is tracked.
class TabProbe {
	int f(int a) {
		if (a > 0) {
			while (a > 1) {
				if (a % 2 == 0) {
					a = a / 2;
				} else {
					a = a - 1;
				}
			}
		}
		return a;
	}
}
