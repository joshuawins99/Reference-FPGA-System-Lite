#include "io.h"
#include "utility.h"

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
    char *index_str;

    if (isQueueEmpty()) {
        Print(1, "Command queue empty");
        return;
    }

    for (i = cmdQueue.head; i < cmdQueue.tail; ++i) {
        index_str = u32_to_ascii(i - cmdQueue.head);

        str_cpy(label, index_str); // copy index into label
        str_cat(label, ": "); // append ": " to the end

        Print(0, label);
        Print(1, cmdQueue.commands[i]);
    }
}

void Print(unsigned char line, const char *data) {
    while (*data) {
        while (ReadIO(UART_CPU_BaseAddress+(2*ADDR_WORD)) != 0); // wait until UART not busy
        WriteIO(UART_CPU_BaseAddress, *data++);
        WriteIO(UART_CPU_BaseAddress+(1*ADDR_WORD), 1);
    }
    if (line) {
        while (ReadIO(UART_CPU_BaseAddress+(2*ADDR_WORD)) != 0);
        WriteIO(UART_CPU_BaseAddress, '\n');
        WriteIO(UART_CPU_BaseAddress+(1*ADDR_WORD), 1);
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
    char *rd_data;

    rd_data = u32_to_ascii(ReadIO32(addr));
    return rd_data;
}

void writeFPGA(uint32_t addr, uint32_t data) {
    WriteIO32(addr, data);
}

uint32_t checkAddress(uint32_t addr_val) {
    if (addr_val & (ADDR_WORD - 1)) return 0;
    return addr_val;
}

ParsedCommand ParseCommand(char *input) {
    ParsedCommand result = {0};
    unsigned char i = 0;
    unsigned char j = 0;
    unsigned char field = 0;
    uint32_t val;
    char current_char;

    while (field < MAX_CMD_ARGS && input[i] != '\0' && input[i] != '\n') {
        j = 0;
        val = 0;

        while ((current_char = input[i]) != ',' && current_char != '\0' && current_char != '\n') {
            if (current_char >= '0' && current_char <= '9') {
                //val = val * 10 + (current_char - '0');
                val = (val << 3) + (val << 1) + (current_char - '0');
            }
            if (j < MAX_TOKEN_LENGTH-1) {
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
    addr_val = checkAddress(cmd_data.values[1]);
    return readFPGA(addr_val);
}

char* writeFPGAWrapper(char *data) {
    ParsedCommand cmd_data;
    uint32_t addr_val;
    cmd_data = ParseCommand(data);
    addr_val = checkAddress(cmd_data.values[1]);
    writeFPGA(addr_val, cmd_data.values[2]);
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

const char READF[]       = "rFPGA";
const char WRITEF[]      = "wFPGA";
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
