/**
 * Simple viewer for RLE images using mmap() and then memory buffer.
 *
 * Note that this is super-simple and omit some required checks, resulting
 * in buffer overflow! Don't use this for untrusted data!
 */
#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>
#include <fcntl.h>
#include <string.h>
#include <stdint.h>

#include "sdl-viewer.h"


typedef int (*unit_processor_t)(const void **mem, void **buffer);
struct rle_handle {
        const void *p;
        const void *mem;
        int fd;
        size_t size;
};

static void
mem_read(const void **buffer, void *dst, unsigned int size)
{
        memcpy(dst, *buffer, size);
        *buffer = (char *)*buffer + size;
}
#define mem_read_autosize(b, d) mem_read(b, d, sizeof(*(d)))

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
unit_processor_color_rgb888(const void **mem, void **buffer)
{
        struct rle_color_rgb888 v;
        uint32_t pixel;

        mem_read_autosize(mem, &v);

        pixel = v.color;
        draw_scanline(buffer, v.length, pixel);

        return 0;
}

static int
unit_processor_color_rgb565(const void **mem, void **buffer)
{
        struct rle_color_rgb565 v;
        uint32_t pixel;

        mem_read_autosize(mem, &v);

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
unit_processor_grayscale(const void **mem, void **buffer)
{
        struct rle_grayscale v;
        uint32_t pixel;

        mem_read_autosize(mem, &v);

        pixel = 0xff000000 | (v.level << 16) | (v.level << 8) | v.level;
        draw_scanline(buffer, v.length, pixel);

        return 0;
}

static int
unit_processor_bitmask(const void **mem, void **buffer)
{
        struct rle_bitmask v;
        uint32_t pixel;

        mem_read_autosize(mem, &v);

        pixel = v.bit ? 0xffffffff : 0xff000000;
        draw_scanline(buffer, v.length, pixel);

        return 0;
}

static int
unit_processor_tinybitmask(const void **mem, void **buffer)
{
        struct rle_tinybitmask v;
        uint32_t pixel;

        mem_read_autosize(mem, &v);

        pixel = v.bit ? 0xffffffff : 0xff000000;
        draw_scanline(buffer, v.length, pixel);

        return 0;
}

static int
decode_line(const void **mem, unit_processor_t unit_processor, void *buffer)
{
        unsigned short n;
        unsigned int i;

        mem_read_autosize(mem, &n);

        for (i = 0; i < n; i++)
                if (unit_processor(mem, &buffer) != 0) {
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
                if (decode_line(&handle->p, unit_processor, buffer) != 0) {
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

        mem_read(&handle->p, v, sizeof(v));

        *w = v[0];
        *h = v[1];
        *unit_type = v[2];

        return 0;
}

rle_handle_t *
rle_open(const char *filename)
{
        rle_handle_t *h;
        struct stat st;

        h = malloc(sizeof(*h));
        if (!h) {
                perror("malloc");
                return NULL;
        }

        h->fd = open(filename, O_RDONLY);
        if (h->fd < 0) {
                perror("open");
                goto free_and_exit;
        }

        if (fstat(h->fd, &st) != 0) {
                perror("fstat");
                goto close_file_free_and_exit;
        }
        h->size = st.st_size;

        h->mem = mmap(NULL, h->size, PROT_READ, MAP_SHARED | MAP_POPULATE,
                      h->fd, 0);
        if (h->mem == MAP_FAILED) {
                perror("mmap");
                goto close_file_free_and_exit;
        }
        h->p = h->mem;

        return h;


close_file_free_and_exit:
        close(h->fd);
free_and_exit:
        free(h);
        return NULL;
}

void
rle_close(rle_handle_t *handle)
{
        munmap((void *)handle->mem, handle->size);
        close(handle->fd);
        free(handle);
}
