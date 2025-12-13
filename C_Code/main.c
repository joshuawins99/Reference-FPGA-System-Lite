#include "fpga_cpu.h"
#include "io.h"

void loop() {
    while (1) {
        ReadUART();
    }
}

int main () {
#ifdef REPL_UART
    Print(1, "Ref FPGA Sys Lite REPL:");
#endif
    loop();
    return 0;
}
