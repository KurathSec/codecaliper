package main

func count(xs []int) int {
	total := 0
	for i := 0; i < len(xs); i++ {
		if xs[i] > 0 {
			total++
		}
	}
	for _, v := range xs {
		total += v
	}
	return total
}
