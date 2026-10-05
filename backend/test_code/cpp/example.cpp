#include <iostream>

int calculate(int x) {
    int unused = 10;
    return x + 1;
}

int main() {
    std::cout << calculate(5) << std::endl;
    return 0;
}
