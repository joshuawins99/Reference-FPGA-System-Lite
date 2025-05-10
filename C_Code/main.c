#include "fpga_cpu.h"
#include "io.c"

unsigned char irq_clear = 0;

void loop() {
    while (1) {
        ReadUART();
    }
}

int main () {
    loop();
    return 0;
}
