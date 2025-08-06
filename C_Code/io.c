#include "io.h"

static CommandQueue cmdQueue = { .head = 0, .tail = 0 };
static unsigned char queueMode = 0; // 0 = immediate, 1 = queue mode

unsigned char isQueueFull() {
    return cmdQueue.tail >= MAX_CMD_QUEUE;
}

unsigned char isQueueEmpty() {
    return cmdQueue.head == cmdQueue.tail;
}

void enqueueCommand(const char *cmd) {
    unsigned char i = 0;
    char current_char;

    if (!isQueueFull()) {
        while (i < MAX_LINE_LENGTH - 1 && (current_char = cmd[i]) != '\0') {
            cmdQueue.commands[cmdQueue.tail][i] = current_char;
            ++i;
        }
        cmdQueue.commands[cmdQueue.tail][i] = '\0';

        ++cmdQueue.tail;
    }
}

char* dequeueCommand() {
    char *cmd;

    if (!isQueueEmpty()) {
        cmd = cmdQueue.commands[cmdQueue.head];
        ++cmdQueue.head;
        return cmd;
    }
    return NULL;
}

void executeQueuedCommands() {
    char *cmd;
    char *result;

    while (!isQueueEmpty()) {
        cmd = dequeueCommand();
        result = executeCommandsSerial(cmd);
        if (result) {
            Print(1, result);
        }
    }
}

void printQueuedCommands() {
    unsigned char i;
    char label[8];

    if (isQueueEmpty()) {
        Print(1, "Command queue empty");
        return;
    }

    for (i = cmdQueue.head; i < cmdQueue.tail; ++i) {
        sprintf(label, "%d: ", i - cmdQueue.head);
        Print(0, label);
        Print(1, cmdQueue.commands[i]);
    }
}

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

char* enterQueueMode(char *data) {
    queueMode = 1;
    return NULL;
}

char* exitQueueMode(char *data) {
    queueMode = 0;
    return NULL;
}

char* runQueueCommands(char *data) {
    queueMode = 0;
    executeQueuedCommands();
    return NULL;
}

char* clearQueue(char *data) {
    cmdQueue.head = 0;
    cmdQueue.tail = 0;
    return NULL;
}

char* printQueueWrapper (char *data) {
    printQueuedCommands();
    return NULL;
}

char* helpWrapper(char *data);

const char READF[]       = "rFPGA,";
const char WRITEF[]      = "wFPGA,";
const char RVERSION[]    = "readFPGAVersion";
const char ENTER_QUEUE[] = "enterQueue";
const char EXIT_QUEUE[]  = "exitQueue";
const char RUN_QUEUE[]   = "runQueue";
const char CLEAR_QUEUE[] = "clearQueue";
const char PRINT_QUEUE[] = "printQueue";
const char HELP[]        = "help";

const command_entry commands[] = {
    {READF,       readFPGAWrapper,    sizeof(READF)-1      },
    {WRITEF,      writeFPGAWrapper,   sizeof(WRITEF)-1     },
    {RVERSION,    ReadVersion,        sizeof(RVERSION)-1   },
    {ENTER_QUEUE, enterQueueMode,     sizeof(ENTER_QUEUE)-1},
    {EXIT_QUEUE,  exitQueueMode,      sizeof(EXIT_QUEUE)-1 },
    {RUN_QUEUE,   runQueueCommands,   sizeof(RUN_QUEUE)-1  },
    {CLEAR_QUEUE, clearQueue,         sizeof(CLEAR_QUEUE)-1},
    {PRINT_QUEUE, printQueueWrapper,  sizeof(PRINT_QUEUE)-1},
    {HELP,        helpWrapper,        sizeof(HELP)-1       }

    // **** Add New Commands Here **** //
};

const unsigned char num_commands = sizeof(commands) / sizeof(commands[0]); //Divide total size in bytes by the size in bytes of a single element

char* helpWrapper (char *data) {
    unsigned char i;

    Print(1, "Available Commands:");
    for (i = 0; i < num_commands; ++i) {
        Print(1,(char *)commands[i].command);
    }
    return NULL;
}

unsigned char stringMatch(const char *a, const char *b, unsigned char len) {
    unsigned char i;

    for (i = 0; i < len; ++i) {
        if (a[i] != b[i]) {
            return 0;  // mismatch
        }
        if (a[i] == '\0') {
            break;  // premature end of string
        }
    }
    return 1;  // match
}

char* executeCommandsSerial(char *data) {
    unsigned char i;
    
    for (i = 0; i < num_commands; ++i) {
        if (stringMatch(data, commands[i].command, commands[i].length) == 1) {
            if (queueMode == 1 && commands[i].command != EXIT_QUEUE) {
                enqueueCommand(data);
                return NULL;
            }
            return commands[i].func(data);
        }
    }
    return NULL;
}

void UARTCommand (char *data) {
    char *commandOutput;

    commandOutput = executeCommandsSerial(data);
    if (commandOutput != NULL) {
        Print(1, commandOutput);
    }
}

void ReadUART() {
    static unsigned char char_iter;
    char *commandOutput;
    static char readuart[MAX_LINE_LENGTH];

    if (ReadIO(UART_CPU_BaseAddress+(4*ADDR_WORD)) == 0) {
        readuart[char_iter] = (char) ReadIO(UART_CPU_BaseAddress+(3*ADDR_WORD));
        if (readuart[char_iter] != '\n') {
            ++char_iter;
        } else {
            readuart[char_iter] = (char) 0;
            char_iter = 0;
            UARTCommand(readuart);
        }
    }
}
