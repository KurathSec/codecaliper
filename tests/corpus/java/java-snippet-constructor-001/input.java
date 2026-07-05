public Matrix(int rows, int cols) {
    if (rows <= 0 || cols <= 0) {
        throw new IllegalArgumentException();
    }
    this.rows = rows;
}
