#include "slice.h"

#define Version_String_BaseAddress 0x8000
#define IO_CPU_BaseAddress         0x9000
#define UART_CPU_BaseAddress       0x9100

#define VersionStringSize 64

#define MAX_CMD_ARGS 3 // Command + arguments
#define MAX_CMD_QUEUE 32
#define MAX_LINE_LENGTH 40
#define MAX_TOKEN_LENGTH 16

#define WriteIO(addr,val)   (*(volatile unsigned char*) (addr) = (val))
#define WriteIO32(addr,val) (*(volatile uint32_t*) (addr) = (val))
#define ReadIO(addr)        (*(volatile unsigned char*) (addr))
#define ReadIO32(addr)      (*(volatile uint32_t*) (addr))

typedef SliceU8 (*command_func)(SliceU8);

#define CMD_ENTRY(str, fn) { { (unsigned char*)(str), sizeof(str)-1 }, fn }

typedef struct {
    const SliceU8 command;
    command_func func;
} command_entry;

typedef struct {
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
void enqueueCommand(const SliceU8);
char* dequeueCommand();
void executeQueuedCommands();
void printQueuedCommands();
void Print (unsigned char, const char *);
void PrintSlice (unsigned char, const SliceU8);
SliceU8 ReadVersion ();
SliceU8 readFPGA (uint32_t);
void writeFPGA (uint32_t, uint32_t);
SliceU8 executeCommandsSerial(SliceU8);
void UARTCommand(SliceU8);
void ReadUART();
uint32_t checkAddress(uint32_t);
ParsedCommand ParseCommand(SliceU8);
