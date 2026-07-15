package main

func tag(ok bool) string {
	x := true
	if ok && x {
		return "yes"
	}
	return "no"
}
