class Search {
    int find(int[][] grid, int target) {
        outer: for (int i = 0; i < grid.length; i++) {
            for (int j = 0; j < grid[i].length; j++) {
                if (grid[i][j] == target) {
                    break outer;
                }
                if (grid[i][j] < 0) {
                    continue outer;
                }
            }
        }
        return target;
    }
}
