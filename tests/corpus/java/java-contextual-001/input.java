record Point(int x, int y) {
    int quadrant() {
        return switch (x) {
            case 0 -> 0;
            default -> {
                yield 1;
            }
        };
    }
}
