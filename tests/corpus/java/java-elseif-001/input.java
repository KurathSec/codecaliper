class Grader {
    int grade(int x) {
        if (x > 90) {
            return 4;
        } else if (x > 80) {
            return 3;
        } else {
            return 2;
        }
    }
}
