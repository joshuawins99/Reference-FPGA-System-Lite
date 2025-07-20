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

char* readFPGA(uint32_t addr) {
    static char rd_data[11];
    sprintf(rd_data, "%u", ReadIO32(addr));
    return rd_data;
}

void writeFPGA(uint32_t addr, uint32_t data) {
    WriteIO32(addr, data);
}

uint32_t checkAddress(uint32_t addr_val) {
    // Check if address is aligned to ADDR_WORD boundary
    if (addr_val % ADDR_WORD != 0) return 0;

    return addr_val;
}

ParsedCommand ParseCommand(char *input) {
    ParsedCommand result = {0};
    unsigned char i = 0;
    unsigned char j = 0;
    unsigned char field = 0;
    uint32_t val;
    char current_char;
    unsigned char command_size = sizeof(result.command) - 1;
    unsigned char rawValues_size = sizeof(result.rawValues[0]) - 1;

    // Parse command
    while ((current_char = input[i]) != ',' && current_char != '\0' && current_char != '\n') {
        if (j < command_size) {
            result.command[j++] = current_char;
        }
        i++;
    }
    result.command[j] = '\0';
    if (input[i] == ',') i++;

    // Parse all values up to MAX_CMD_ARGS
    while (field < MAX_CMD_ARGS && input[i] != '\0' && input[i] != '\n') {
        j = 0;
        val = 0;

        while ((current_char = input[i]) != ',' && current_char != '\0' && current_char != '\n') {
            if (current_char >= '0' && current_char <= '9') {
                //val = val * 10 + (input[i] - '0');
                val = (val << 3) + (val << 1) + (current_char - '0');
            }
            if (j < rawValues_size) {
                result.rawValues[field][j++] = current_char;
            }
            i++;
        }

        result.rawValues[field][j] = '\0';
        result.values[field] = val;
        field++;

        if (input[i] == ',') i++;
    }

    result.valueCount = field;
    return result;
}

char* readFPGAWrapper(char *data) {
    ParsedCommand cmd_data;
    uint32_t addr_val;
    cmd_data = ParseCommand(data);
    addr_val = checkAddress(cmd_data.values[0]);
    return readFPGA(addr_val);
}

char* writeFPGAWrapper(char *data) {
    ParsedCommand cmd_data;
    uint32_t addr_val;
    cmd_data = ParseCommand(data);
    addr_val = checkAddress(cmd_data.values[0]);
    writeFPGA(addr_val, cmd_data.values[1]);
    return NULL;
}

const char READF[]    = "rFPGA,";
const char WRITEF[]   = "wFPGA,";
const char RVERSION[] = "readFPGAVersion";

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
