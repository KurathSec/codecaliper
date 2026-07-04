class Guard {
    static boolean check(int a, int b, boolean flag) {
        try {
            if (a > 0 && b > 0 && flag) {
                return true;
            }
        } catch (RuntimeException e) {
            return false;
        }
        return false;
    }
}
