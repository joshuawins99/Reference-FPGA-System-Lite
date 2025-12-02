#include "utility.h"
char* str_cpy(char* dest, const char* src) {
    int i = 0;
    while (src[i] != '\0') {
        dest[i] = src[i];
        i++;
    }
    dest[i] = '\0';
    return dest;
}

char* str_cat(char* dest, const char* src) {
    int i = 0;
    // Find end of dest
    while (dest[i] != '\0') {
        i++;
    }

    int j = 0;
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

unsigned char stringMatch(const char *a, const char *b, unsigned char len) {
    unsigned char i;

    for (i = 0; i < len; ++i) {
        if (a[i] != b[i]) return 0;
    }
    return 1;
}

unsigned char stringMatchSlice(SliceU8 a, SliceU8 b) {
    slen_t i;
    if (a.len < b.len) return 0;

    for (i = 0; i < b.len; ++i) {
        if (a.ptr[i] != b.ptr[i]) return 0;
    }
    return 1;
}
