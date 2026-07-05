class Choice {
    int pick(int a, int b) {
        int hi = a > b ? a : b;
        int sign = a > 0 ? 1 : (a < 0 ? -1 : 0);
        return hi + sign;
    }
}
