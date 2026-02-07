#ifndef UTILITY_H
#define UTILITY_H

#include "slice.h"
#include "fpga_cpu.h"

#define MAX_CMD_ARGS 3 // Command + arguments
#define MAX_TOKEN_LENGTH 16

#define TOKENIZER_SEPARATOR ','

typedef struct {
    char rawValues[MAX_CMD_ARGS][MAX_TOKEN_LENGTH]; // Raw strings for each value
    uint32_t values[MAX_CMD_ARGS];                  // Parsed integers
    uint8_t valueCount;                             // Actual number of values found
} ParsedCommand;

char* str_cpy(char *, const char *);
char* str_cat(char *, const char *);
char* u32_to_ascii(uint32_t);
uint8_t stringMatch(const char *, const char *, uint8_t);
uint8_t stringMatchSlicePrefix(SliceU8, SliceU8);
uint8_t stringMatchSlice(SliceU8, SliceU8);
uint32_t checkAddress(uint32_t);
ParsedCommand ParseCommand(SliceU8);
uint8_t numParsedArguments (ParsedCommand);

#endif