#ifndef __SDL_VIEWER_H__
#define __SDL_VIEWER_H__ 1

#include <rle.h>

#define BPP 32

typedef struct rle_handle rle_handle_t;

rle_handle_t *rle_open(const char *filename);
void rle_close(rle_handle_t *handle);

int rle_parse_header(rle_handle_t *handle, unsigned short *w, unsigned short *h, rle_unit_type_t *unit_type);
int rle_decode(rle_handle_t *handle, unsigned short h, rle_unit_type_t unit_type, void *buffer, unsigned short pitch);

#endif /* __SDL_VIEWER_H__ */
