#include "io.h"

static CommandQueue cmdQueue = { .head = 0, .tail = 0 };
static uint8_t queueMode = 0; // 0 = immediate, 1 = queue mode

uint8_t isQueueFull() {
    return cmdQueue.tail >= MAX_CMD_QUEUE;
}

uint8_t isQueueEmpty() {
    return cmdQueue.head == cmdQueue.tail;
}

void enqueueCommand(SliceU8 data) {
    uint8_t i = 0;

    if (!isQueueFull()) {
        while (i < data.len) {
            cmdQueue.commands[cmdQueue.tail][i] = data.ptr[i];
            ++i;
        }
        cmdQueue.slice_lengths[cmdQueue.tail] = data.len;
        cmdQueue.commands[cmdQueue.tail][i] = '\0';

        ++cmdQueue.tail;
    }
}

SliceU8 dequeueCommand() {
    uint8_t idx = cmdQueue.head;
    
    if (!isQueueEmpty()) {
        ++cmdQueue.head;
        return slice_range((unsigned char *)cmdQueue.commands[idx], 0, cmdQueue.slice_lengths[idx]);
    }
    return cstr_to_slice(NULL);
}

void executeQueuedCommands() {
    SliceU8 cmd;
    SliceU8 result;

    while (!isQueueEmpty()) {
        cmd = dequeueCommand();
        result = executeCommandsSerial(cmd);
        if (result.ptr != NULL && result.len > 0) {
            PrintSlice(1, result);
        }
    }
}

void printQueuedCommands() {
    uint8_t i;
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
        PrintSlice(1, slice_range((unsigned char *)cmdQueue.commands[i], 0, cmdQueue.slice_lengths[i]));
    }
}

void Print(uint8_t line, const char *data) {
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

void PrintSlice(uint8_t line, const SliceU8 data) {
    char *ptr = (char *)data.ptr; // Printing ascii so use char
    slen_t length = data.len;

    while (length--) {
        while (ReadIO(UART_CPU_BaseAddress+(2*ADDR_WORD)) != 0); // wait until UART not busy
        WriteIO(UART_CPU_BaseAddress, *ptr++);
        WriteIO(UART_CPU_BaseAddress+(1*ADDR_WORD), 1);
    }
    if (line) {
        while (ReadIO(UART_CPU_BaseAddress+(2*ADDR_WORD)) != 0);
        WriteIO(UART_CPU_BaseAddress, '\n');
        WriteIO(UART_CPU_BaseAddress+(1*ADDR_WORD), 1);
    }
}

SliceU8 ReadVersion() {
    static char readversion[VersionStringSize+1];
    char current_char;
    uint8_t count = 0;
    uint8_t i;

    for (i = 0; i < VersionStringSize; ++i) {
        current_char = (char) ReadIO(Version_String_BaseAddress+(i*ADDR_WORD));
        if (current_char == '\0') {
            ++count;
        } else {
            readversion[i-count] = current_char;
        }
    }
    
    return slice_range((uint8_t *)readversion, 0, (i-count));
}

SliceU8 readFPGA(uint32_t addr) {
    char *rd_data;
    
    rd_data = u32_to_ascii(ReadIO32(addr));
    return cstr_to_slice(rd_data);
}

void writeFPGA(uint32_t addr, uint32_t data) {
    WriteIO32(addr, data);
}

SliceU8 readFPGAWrapper(SliceU8 data) {
    ParsedCommand cmd_data;
    uint32_t addr_val;
    cmd_data = ParseCommand(data);
    addr_val = checkAddress(cmd_data.values[1]);
    return readFPGA(addr_val);
}

SliceU8 writeFPGAWrapper(SliceU8 data) {
    ParsedCommand cmd_data;
    uint32_t addr_val;
    cmd_data = ParseCommand(data);
    addr_val = checkAddress(cmd_data.values[1]);
    writeFPGA(addr_val, cmd_data.values[2]);
    return cstr_to_slice(NULL);
}

SliceU8 enterQueueMode(SliceU8 data) {
    queueMode = 1;
    return cstr_to_slice(NULL);
}

SliceU8 exitQueueMode(SliceU8 data) {
    queueMode = 0;
    return cstr_to_slice(NULL);
}

SliceU8 runQueueCommands(SliceU8 data) {
    queueMode = 0;
    executeQueuedCommands();
    return cstr_to_slice(NULL);
}

SliceU8 clearQueue(SliceU8 data) {
    cmdQueue.head = 0;
    cmdQueue.tail = 0;
    return cstr_to_slice(NULL);
}

SliceU8 printQueueWrapper (SliceU8 data) {
    printQueuedCommands();
    return cstr_to_slice(NULL);
}

SliceU8 helpWrapper(SliceU8 data);

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
    CMD_ENTRY(READF,       readFPGAWrapper  ),
    CMD_ENTRY(WRITEF,      writeFPGAWrapper ),
    CMD_ENTRY(RVERSION,    ReadVersion      ),
    CMD_ENTRY(ENTER_QUEUE, enterQueueMode   ),
    CMD_ENTRY(EXIT_QUEUE,  exitQueueMode    ),
    CMD_ENTRY(RUN_QUEUE,   runQueueCommands ),
    CMD_ENTRY(CLEAR_QUEUE, clearQueue       ),
    CMD_ENTRY(PRINT_QUEUE, printQueueWrapper),
    CMD_ENTRY(HELP,        helpWrapper      )

    // **** Add New Commands Here **** //
};

const uint8_t num_commands = sizeof(commands) / sizeof(commands[0]); //Divide total size in bytes by the size in bytes of a single element

SliceU8 helpWrapper (SliceU8 data) {
    uint8_t i;

    Print(1, "Available Commands:");
    for (i = 0; i < num_commands; ++i) {
        Print(1,(char *)commands[i].command.ptr);
    }
    return cstr_to_slice(NULL);
}

SliceU8 executeCommandsSerial(SliceU8 data) {
    uint8_t i;
    
    for (i = 0; i < num_commands; ++i) {
        if (stringMatchSlice(data, commands[i].command) == 1) {
            if (queueMode == 1 && commands[i].command.ptr != (const uint8_t*)EXIT_QUEUE) {
                enqueueCommand(data);
                return cstr_to_slice(NULL);
            }
            return commands[i].func(data);
        }
    }
    return cstr_to_slice(NULL);
}

void UARTCommand (SliceU8 data) {
    SliceU8 commandOutput;

    commandOutput = executeCommandsSerial(data);
    if (commandOutput.ptr != NULL && commandOutput.len > 0) {
        PrintSlice(1, commandOutput);
    }
}

void ReadUART() {
    static uint8_t char_iter;
    static char readuart[MAX_LINE_LENGTH];

    if (ReadIO(UART_CPU_BaseAddress+(4*ADDR_WORD)) == 0) {
        readuart[char_iter] = (char) ReadIO(UART_CPU_BaseAddress+(3*ADDR_WORD));
        if (readuart[char_iter] != '\n') {
            ++char_iter;
        } else {
            UARTCommand(slice_range_safe((uint8_t *)readuart, MAX_LINE_LENGTH, 0, char_iter));
            char_iter = 0;
        }
    }
}
