package main

func check(a, b, c bool) bool {
	if a && b && c {
		return true
	}
	return a && b || c
}
