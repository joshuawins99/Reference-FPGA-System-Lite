#define Version_String_BaseAddress 0x8000
#define IO_CPU_BaseAddress         0x9000
#define UART_CPU_BaseAddress       0x9100

#define VersionStringSize 64

#define MAX_CMD_ARGS 2
#define MAX_CMD_QUEUE 32
#define MAX_LINE_LENGTH 40
#define MAX_TOKEN_LENGTH 16

#define WriteIO(addr,val)   (*(volatile unsigned char*) (addr) = (val))
#define WriteIO32(addr,val) (*(volatile uint32_t*) (addr) = (val))
#define ReadIO(addr)        (*(volatile unsigned char*) (addr))
#define ReadIO32(addr)      (*(volatile uint32_t*) (addr))

typedef char* (*command_func)(char*);

typedef struct {
    const char *command;
    command_func func;
    unsigned char length;
} command_entry;

typedef struct {
    char command[MAX_TOKEN_LENGTH];                 // Command name
    char rawValues[MAX_CMD_ARGS][MAX_TOKEN_LENGTH]; // Raw strings for each value
    uint32_t values[MAX_CMD_ARGS];                  // Parsed integers
    unsigned char valueCount;                       // Actual number of values found
} ParsedCommand;

typedef struct {
    char commands[MAX_CMD_QUEUE][MAX_LINE_LENGTH];
    unsigned char head;
    unsigned char tail;
} CommandQueue;

unsigned char isQueueFull();
unsigned char isQueueEmpty();
void enqueueCommand(const char *);
char* dequeueCommand();
void executeQueuedCommands();
void printQueuedCommands();
void Print (unsigned char, char *);
char* ReadVersion ();
char* readFPGA (uint32_t);
void writeFPGA (uint32_t, uint32_t);
unsigned char stringMatch (const char *, const char *, unsigned char);
char* executeCommandsSerial(char *);
void UARTCommand(char *);
void ReadUART();
uint32_t checkAddress(uint32_t);
ParsedCommand ParseCommand(char *);

