#ifndef IO_H
#define IO_H

#include "slice.h"
#include "utility.h"
#include "fpga_cpu.h"

#define Version_String_BaseAddress 0x8000
#define IO_CPU_BaseAddress         0x9000
#define UART_CPU_BaseAddress       0x9100

#define VersionStringSize 64

#define MAX_CMD_QUEUE 32
#define MAX_LINE_LENGTH 40

#define WriteIO(addr,val)   (*(volatile uint8_t*) (addr) = (val))
#define WriteIO32(addr,val) (*(volatile uint32_t*) (addr) = (val))
#define ReadIO(addr)        (*(volatile uint8_t*) (addr))
#define ReadIO32(addr)      (*(volatile uint32_t*) (addr))

typedef SliceU8 (*command_func)(SliceU8);

#define CMD_ENTRY(str, fn) { { (uint8_t*)(str), sizeof(str)-1 }, fn }

typedef struct {
    const SliceU8 command;
    command_func func;
} command_entry;

typedef struct {
    char commands[MAX_CMD_QUEUE][MAX_LINE_LENGTH];
    slen_t slice_lengths[MAX_CMD_QUEUE];
    uint8_t head;
    uint8_t tail;
} CommandQueue;

uint8_t isQueueFull();
uint8_t isQueueEmpty();
void enqueueCommand(const SliceU8);
SliceU8 dequeueCommand();
void executeQueuedCommands();
void printQueuedCommands();
void Print (uint8_t, const char *);
void PrintSlice (uint8_t, const SliceU8);
SliceU8 ReadVersion ();
SliceU8 readFPGA (uint32_t);
void writeFPGA (uint32_t, uint32_t);
SliceU8 executeCommandsSerial(SliceU8);
void UARTCommand(SliceU8);
void ReadUART();

#endif