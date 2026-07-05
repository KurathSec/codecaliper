class Signal {
    String describe(int code) {
        switch (code) {
            case 1:
                return "one";
            case 2:
                return "two";
            case 3:
                return "three";
            default:
                return "many";
        }
    }
}
