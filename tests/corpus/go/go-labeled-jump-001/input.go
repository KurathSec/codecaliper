package main

func search(grid [][]int, target int) bool {
Found:
	for _, row := range grid {
		for _, v := range row {
			if v == target {
				break Found
			}
		}
	}
	return false
}
