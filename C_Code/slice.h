#ifndef SLICE_H
#define SLICE_H

#include <stdint.h>

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

SliceU8 slice_range_safe(uint8_t *, slen_t, slen_t, slen_t);
SliceU8 slice_len_safe(uint8_t *, slen_t, slen_t, slen_t);
SliceU8 slice_range(uint8_t *, slen_t, slen_t);
SliceU8 slice_len(uint8_t *, slen_t, slen_t);
SliceU8 subslice(SliceU8, slen_t, slen_t);
uint8_t slice_equal(SliceU8, SliceU8);
uint8_t slice_get(SliceU8, slen_t);
void slice_to_cstr(SliceU8, char *, slen_t);
SliceU8 cstr_to_slice(char *);

#endif //SLICE_H
