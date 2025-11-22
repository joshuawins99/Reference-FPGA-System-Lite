#include "fpga_cpu.h"
#include "utility.c"
#include "io.c"

void loop() {
    while (1) {
        ReadUART();
    }
}

int main () {
    loop();
    return 0;
}
