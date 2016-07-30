/**
 * Simple viewer for RLE images using SDL and fread() calls.
 *
 * Note that this is super-simple and omit some required checks, resulting
 * in buffer overflow! Don't use this for untrusted data!
 */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

#include "sdl-viewer.h"

typedef int (*unit_processor_t)(FILE *fp, void **buffer);
struct rle_handle {
        FILE *fp;
};

static void
draw_scanline(void **buffer, unsigned length, uint32_t pixel)
{
        uint32_t *p;
        unsigned int i;

        for (i = 0, p = *buffer; i < length; i++, p++)
                *p = pixel;

        *buffer = p;
}

static int
unit_processor_color_rgb888(FILE *fp, void **buffer)
{
        struct rle_color_rgb888 v;
        uint32_t pixel;

        if (fread(&v, sizeof(v), 1, fp) != 1) {
                perror("fread: could not read unit.");
                return -1;
        }

        pixel = v.color;
        draw_scanline(buffer, v.length, pixel);

        return 0;
}

static int
unit_processor_color_rgb565(FILE *fp, void **buffer)
{
        struct rle_color_rgb565 v;
        uint32_t pixel;

        if (fread(&v, sizeof(v), 1, fp) != 1) {
                perror("fread: could not read unit.");
                return -1;
        }

        if (v.color == 0xffff)
            pixel = 0xffffffff;
        else if (v.color == 0x0000)
            pixel = 0xff000000;
        else {
            uint32_t r, g, b;

            r = (v.color >> 11) & 0x1f;
            g = (v.color >> 5) & 0x3f;
            b = v.color & 0x1f;

            pixel = 0xff000000 | (r << (16 + 3)) | (g << (8 + 2)) | (b << 3);
        }

        draw_scanline(buffer, v.length, pixel);

        return 0;
}

static int
unit_processor_grayscale(FILE *fp, void **buffer)
{
        struct rle_grayscale v;
        uint32_t pixel;

        if (fread(&v, sizeof(v), 1, fp) != 1) {
                perror("fread: could not read unit.");
                return -1;
        }

        pixel = 0xff000000 | (v.level << 16) | (v.level << 8) | v.level;
        draw_scanline(buffer, v.length, pixel);

        return 0;
}

static int
unit_processor_bitmask(FILE *fp, void **buffer)
{
        struct rle_bitmask v;
        uint32_t pixel;

        if (fread(&v, sizeof(v), 1, fp) != 1) {
                perror("fread: could not read unit.");
                return -1;
        }

        pixel = v.bit ? 0xffffffff : 0xff000000;
        draw_scanline(buffer, v.length, pixel);

        return 0;
}

static int
unit_processor_tinybitmask(FILE *fp, void **buffer)
{
        struct rle_tinybitmask v;
        uint32_t pixel;

        if (fread(&v, sizeof(v), 1, fp) != 1) {
                perror("fread: could not read unit.");
                return -1;
        }

        pixel = v.bit ? 0xffffffff : 0xff000000;
        draw_scanline(buffer, v.length, pixel);

        return 0;
}

static int
decode_line(FILE *fp, unit_processor_t unit_processor, void *buffer)
{
        unsigned short n;
        unsigned int i;

        if (fread(&n, sizeof(n), 1, fp) != 1) {
                perror("fread: could not read number of elements in line.");
                return -1;
        }

        for (i = 0; i < n; i++)
                /* XXX SECURITY ISSUE:
                 * XXX for simplicity sake, this doesn't check for buffer
                 * XXX being past the line end, unit_processor() is free
                 * XXX to overflow the buffer.
                 * XXX DON'T USE THIS FOR UNTRUSTED DATA!
                 */
                if (unit_processor(fp, &buffer) != 0) {
                        fprintf(stderr, "Could not process unit %d\n", i);
                        return -1;
                }

        return 0;
}


int
rle_decode(rle_handle_t *handle, unsigned short h, rle_unit_type_t unit_type, void *buffer, unsigned short pitch)
{
        unsigned int i;
        unit_processor_t unit_processor;
        const unit_processor_t unit_processors[] = {
                unit_processor_color_rgb888,
                unit_processor_color_rgb565,
                unit_processor_grayscale,
                unit_processor_bitmask,
                unit_processor_tinybitmask
        };

        unit_processor = unit_processors[unit_type];

        for (i = 0; i < h; i++) {
                if (decode_line(handle->fp, unit_processor, buffer) != 0) {
                        fprintf(stderr, "Problems decoding line %d\n", i);
                        return -1;
                }
                buffer = (char *)buffer + pitch;
        }
        return 0;
}

int
rle_parse_header(rle_handle_t *handle, unsigned short *w, unsigned short *h, rle_unit_type_t *unit_type)
{
        unsigned short v[4] = {0, 0, 0, 0};

        if (fread(v, sizeof(v[0]), 4, handle->fp) != 4)
                return -1;

        *w = v[0];
        *h = v[1];
        *unit_type = v[2];

        return 0;
}

rle_handle_t *
rle_open(const char *filename)
{
        rle_handle_t *h;
        FILE *fp;

        fp = fopen(filename, "rb");
        if (!fp) {
                perror("fopen");
                return NULL;
        }

        h = malloc(sizeof(*h));
        if (!h) {
                perror("malloc");
                fclose(fp);
                return NULL;
        }

        h->fp = fp;
        return h;
}

void
rle_close(rle_handle_t *handle)
{
        fclose(handle->fp);
        free(handle);
}
