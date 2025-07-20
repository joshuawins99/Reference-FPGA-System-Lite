#define Version_String_BaseAddress 0x8000
#define IO_CPU_BaseAddress         0x9000
#define UART_CPU_BaseAddress       0x9100

#define VersionStringSize 64

#define MAX_CMD_ARGS 2

#define WriteIO(addr,val)       (*(volatile unsigned char*) (addr) = (val))
#define WriteIO32(addr,val)     (*(volatile uint32_t*) (addr) = (val))
#define ReadIO(addr)            (*(volatile unsigned char*) (addr))
#define ReadIO32(addr)          (*(volatile uint32_t*) (addr))

typedef char* (*command_func)(char*);

typedef struct {
    const char *command;
    command_func func;
    unsigned char length;
} command_entry;

typedef struct {
    char command[16];                 // Command name
    char rawValues[MAX_CMD_ARGS][16]; // Raw strings for each value
    uint32_t values[MAX_CMD_ARGS];    // Parsed integers
    unsigned char valueCount;         // Actual number of values found
} ParsedCommand;

void Print (unsigned char, char *);
char* ReadVersion ();
char* readFPGA (uint32_t);
void writeFPGA (uint32_t, uint32_t);
char* executeCommandsSerial(char *);
void ReadUART();
uint32_t checkAddress(uint32_t);
ParsedCommand ParseCommand(char *);

