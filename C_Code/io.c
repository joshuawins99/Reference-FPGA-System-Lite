#include "io.h"

void Print(unsigned char line, char *data) {
    unsigned char busy_status = 0;
    unsigned char iterator = 0;
    unsigned char strlength = strlen(data);

    while (iterator < strlength || (line && iterator == strlength)) {
        busy_status = ReadIO(UART_CPU_BaseAddress+(2*ADDR_WORD));
        if (busy_status == 0) {
            if (iterator < strlength) {
                WriteIO(UART_CPU_BaseAddress, data[iterator]);
                ++iterator;
            } else if (line) {
                WriteIO(UART_CPU_BaseAddress, '\n');
                line = 0;  // To exit the loop after writing the newline character
            }
            WriteIO(UART_CPU_BaseAddress+(1*ADDR_WORD), 1);
        }
    }
}

char* ReadVersion() {
    static char readversion[VersionStringSize];
    char current_char;
    unsigned char count = 0;
    unsigned char i;

    for (i = 0; i < VersionStringSize; ++i) {
        current_char = (char) ReadIO(Version_String_BaseAddress+(i*ADDR_WORD));
        if (current_char == '\0') {
            ++count;
        } else {
            readversion[i-count] = current_char;
        }
    }
    return readversion;
}

char* readFPGA(char *addr) {
    static char rd_data[11];

    sprintf(rd_data, "%u", ReadIO32(atoi(addr)));
    return rd_data;
}

void writeFPGA(char *addr, char *data) {
    WriteIO32(atoi(addr), strtoul(data, NULL, 10));
}

typedef char* (*command_func)(char*);

typedef struct {
    const char *command;
    command_func func;
    unsigned char length;
} command_entry;

const char READF[]    = "rFPGA,";
const char WRITEF[]   = "wFPGA,";
const char RVERSION[] = "readFPGAVersion";

char* readFPGAWrapper(char *data) {
    static char addr_sub[6];
    strncpy(addr_sub, data + 6, strlen(data) - 6);
    return readFPGA(&addr_sub[0]);
}

char* writeFPGAWrapper(char *data) {
    static char addr_sub[6];
    static char data_sub[11];
    unsigned char j = 0;
    unsigned char k = 0;
    unsigned char address_done = 0;

    for (j = 6; j <= (strlen(data)); ++j) {
        if (data[j] != ',' && address_done == 0) {
            addr_sub[j - 6] = data[j];
        } else if (data[j] != '\n' && data[j] != '\r' && data[j] != ',') {
            data_sub[k] = data[j];
            ++k;
        } else {
            address_done = 1;
        }
    }
    writeFPGA(&addr_sub[0], &data_sub[0]);
    return NULL;
}

const command_entry commands[] = {
    {READF,    readFPGAWrapper,    sizeof(READF)-1   },
    {WRITEF,   writeFPGAWrapper,   sizeof(WRITEF)-1  },
    {RVERSION, ReadVersion,        sizeof(RVERSION)-1}

    // **** Add New Commands Here **** //
};

const unsigned char num_commands = sizeof(commands) / sizeof(commands[0]); //Divide total size in bytes by the size in bytes of a single element

char* executeCommandsSerial(char *data) {
    unsigned char i;

    for (i = 0; i < num_commands; ++i) {
        if (strncmp(data, commands[i].command, commands[i].length) == 0) {
            return commands[i].func(data);
        }
    }
    return NULL;
}

void ReadUART() {
    static unsigned char char_iter;
    char *commandOutput;
    static char readuart[40];

    if (ReadIO(UART_CPU_BaseAddress+(4*ADDR_WORD)) == 0) {
        readuart[char_iter] = (char) ReadIO(UART_CPU_BaseAddress+(3*ADDR_WORD));
        if (readuart[char_iter] != '\n') {
            ++char_iter;
        } else {
            readuart[char_iter] = (char) 0;
            char_iter = 0;
            commandOutput = executeCommandsSerial(&readuart[0]);
            if (commandOutput != NULL) {
                Print(1, commandOutput);
            }
        }
    }
}
