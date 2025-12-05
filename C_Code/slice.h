#ifndef SLICE_H
#define SLICE_H

typedef uint8_t slen_t;

typedef struct {
    uint8_t *ptr;
    slen_t len;
} SliceU8;

//Define SLICE_CHECKS before including this header to enable safety checks
#ifdef SLICE_CHECKS
#  define SLICE_RUNTIME_CHECK(cond) if (!(cond)) return (SliceU8){0,0}
#  define SLICE_RUNTIME_CHECK_GET(cond) if (!(cond)) return 0
#  define SLICE_RUNTIME_CHECK_VOID(cond) if (!(cond)) return
#else
#  define SLICE_RUNTIME_CHECK(cond) ((void)0)
#  define SLICE_RUNTIME_CHECK_GET(cond) ((void)0)
#  define SLICE_RUNTIME_CHECK_VOID(cond) ((void)0)
#endif

//Range-style safe: buf[start..end]
SliceU8 slice_range_safe(uint8_t *buf, slen_t buf_len, slen_t start, slen_t end) {
    SLICE_RUNTIME_CHECK(start <= end && end <= buf_len);

    return (SliceU8){ buf + start, end - start };
}

//Length-style safe: buf[start..start+length]
SliceU8 slice_len_safe(uint8_t *buf, slen_t buf_len, slen_t start, slen_t length) {
    SLICE_RUNTIME_CHECK(start + length <= buf_len);

    return (SliceU8){ buf + start, length };
}

//Range-style: buf[start..end]
SliceU8 slice_range(uint8_t *buf, slen_t start, slen_t end) {
    SLICE_RUNTIME_CHECK(start <= end);

    return (SliceU8){ buf + start, end - start };
}

//Length-style: buf[start..start+length]
SliceU8 slice_len(uint8_t *buf, slen_t start, slen_t length) {

    return (SliceU8){ buf + start, length };
}

//Create a subslice
SliceU8 subslice(SliceU8 s, slen_t start, slen_t length) {
    SLICE_RUNTIME_CHECK(start + length <= s.len);

    return (SliceU8){ s.ptr + start, length };
}

//Compare two slices
uint8_t slice_equal(SliceU8 a, SliceU8 b) {
    slen_t i;
    if (a.len != b.len) return 0;
    for (i = 0; i < a.len; i++) {
        if (a.ptr[i] != b.ptr[i]) return 0;
    }
    return 1;
}

//Safe access
uint8_t slice_get(SliceU8 s, slen_t index) {
    SLICE_RUNTIME_CHECK_GET(index < s.len);
    return s.ptr[index];
}

//Convert slice -> null-terminated string
void slice_to_cstr(SliceU8 s, char *dest, slen_t dest_size) {
    slen_t i;
    SLICE_RUNTIME_CHECK_VOID(dest_size > 0);

    if (s.len + 1 > dest_size) s.len = dest_size - 1;
    for (i = 0; i < s.len; i++) {
        dest[i] = (char)s.ptr[i];
    }
    dest[s.len] = '\0';
}

//Convert null-terminated string -> slice
SliceU8 cstr_to_slice(char *cstr) {
    slen_t len = 0;
    if (cstr == NULL) {
        //Explicit empty slice
        return (SliceU8){ .ptr = NULL, .len = 0 };
    }
    while (cstr[len] != '\0') len++;
    return (SliceU8){ (unsigned char*)cstr, len };
}

#endif //SLICE_H
