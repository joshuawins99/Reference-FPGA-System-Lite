#include "utility.h"

char* str_cpy(char* dest, const char* src) {
    uint32_t i = 0;
    while (src[i] != '\0') {
        dest[i] = src[i];
        i++;
    }
    dest[i] = '\0';
    return dest;
}

char* str_cat(char* dest, const char* src) {
    uint32_t i = 0;
    // Find end of dest
    while (dest[i] != '\0') {
        i++;
    }

    uint32_t j = 0;
    // Copy src to end of dest
    while (src[j] != '\0') {
        dest[i] = src[j];
        i++;
        j++;
    }

    dest[i] = '\0';
    return dest;
}

char* u32_to_ascii(uint32_t value) {
    static char buf[11]; // 10 digits + null
    char *p = buf + 10;
    *p = '\0';
    do {
        *--p = '0' + (value % 10);
        value /= 10;
    } while (value);
    return p;
}

uint8_t stringMatch(const char *a, const char *b, uint8_t len) {
    uint8_t i;

    for (i = 0; i < len; ++i) {
        if (a[i] != b[i]) return 0;
    }
    return 1;
}

uint8_t stringMatchSlice(SliceU8 a, SliceU8 b) {
    slen_t i;
    if (a.len < b.len) return 0;

    for (i = 0; i < b.len; ++i) {
        if (a.ptr[i] != b.ptr[i]) return 0;
    }
    return 1;
}

uint32_t checkAddress(uint32_t addr_val) {
    if (addr_val & (ADDR_WORD - 1)) return 0;
    return addr_val;
}

ParsedCommand ParseCommand(SliceU8 input) {
    ParsedCommand result = {0};
    slen_t i = 0;
    uint8_t j = 0;
    uint8_t field = 0;
    uint32_t val;
    char current_char;

    while (field < MAX_CMD_ARGS && i < input.len && input.ptr[i] != '\n') {
        j = 0;
        val = 0;

        while (i < input.len && (current_char = input.ptr[i]) != ',' && current_char != '\n') {
            if (current_char >= '0' && current_char <= '9') {
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

        if (input.ptr[i] == ',') i++;
    }

    result.valueCount = field;
    return result;
}
