int add(int a, int b) {
    return a + b;
}

int main(void) {
    int i = 0;
    int total = 0;
    while (i < 10) {
        if (i < 5) {
            total = add(total, i);
        } else {
            total = total + 1;
        }
        i = i + 1;
    }
    return total;
}
