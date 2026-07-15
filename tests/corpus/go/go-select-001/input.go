package main

func recv(a, b chan int) int {
	select {
	case x := <-a:
		return x
	case y := <-b:
		return y
	default:
		return 0
	}
}
