class Loops {
    int tally(int[] xs) {
        int total = 0;
        for (int i = 0; i < 3; i++) {
            while (total < 100) {
                total += i;
            }
        }
        for (int x : xs) {
            total += x;
        }
        do {
            total--;
        } while (total > 10);
        return total;
    }
}
