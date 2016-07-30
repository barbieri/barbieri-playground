/**
 * This outputs images compressed with RLE (Run Length Encoding) using
 * custom rle units.
 *
 * Output format is composed of:
 *  - header of 4 'unsigned short': width, height, unit_type and reserved.
 *  - 'height' rle lines for format:
 *     - 'unsigned short' length as number of units (always less then 'width')
 *     - 'length' units that are dependent of 'unit_type'
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include "rle.h"

struct rle
{
    unsigned int color;
    unsigned int length;
};

typedef void (*output_unit_t)(FILE *fp, const struct rle *rle);
typedef void (*output_line_t)(output_unit_t output_unit, FILE *fp, const struct rle *rles, int rles_length);

static int
parse_ppm(FILE *fp, int *w, int *h, int *maxval)
{
    if (fscanf(fp, "P6 %d %d %d", w, h, maxval) != 3) {
        fputs("Not simple PPM (P6 without comments) file.\n", stderr);
        return -1;
    }
    return !isspace(fgetc(fp));
}

static inline unsigned int
rgb_from_components(unsigned char r, unsigned char g, unsigned char b)
{
    return (r << 16) | (g << 8) | b;
}

static int
read_color_char(FILE *fp, unsigned int *rgb)
{
    unsigned char v[3];

    if (fread(&v, sizeof(unsigned char), 3, fp) != 3)
        return -1;

    *rgb = rgb_from_components(v[0], v[1], v[2]);
    return 0;
}

static int
read_color_short(FILE *fp, unsigned int *rgb)
{
    unsigned short v[3];

    if (fread(&v, sizeof(unsigned short), 3, fp) != 3)
        return -1;

    *rgb = rgb_from_components(v[0] >> 8, v[1] >> 8, v[2] >> 8);
    return 0;
}

static inline void
output_header(FILE *fp, unsigned short w, unsigned short h, rle_unit_type_t unit_type)
{
    unsigned short v[4] = {w, h, unit_type, 0};

    fwrite(v, sizeof(v[0]), 4, fp);
}

static void
output_unit_color_rgb888(FILE *fp, const struct rle *rle)
{
    struct rle_color_rgb888 v;

    v.color = rle->color;
    v.length = rle->length;

    fwrite(&v, sizeof(v), 1, fp);
}

static void
output_unit_color_rgb565(FILE *fp, const struct rle *rle)
{
    struct rle_color_rgb565 v;
    unsigned char r, g, b;

    r = (rle->color & 0xff0000) >> (16 + 3);
    g = (rle->color & 0x00ff00) >> (8 + 2);
    b = (rle->color & 0xff) >> 3;

    v.color = (r << 11) | (g << 5) | b;

    if (rle->length & ~0x0000ffff)
        fprintf(stderr,
                "ERROR: rle.length (%d) is too big for rgb565!\n",
                rle->length);

    v.length = rle->length;

    fwrite(&v, sizeof(v), 1, fp);
}

static void
output_unit_grayscale(FILE *fp, const struct rle *rle)
{
    struct rle_grayscale v;
    unsigned int r, g, b;

    if (rle->length & ~0x00ffffff)
        fprintf(stderr,
                "ERROR: rle.length (%d) is too big for grayscale!\n",
                rle->length);

    r = (rle->color & 0xff0000) >> 16;
    g = (rle->color & 0x00ff00) >> 8;
    b = rle->color & 0xff;

    v.level = (r + g + b) / 3;
    v.length = rle->length & 0x00ffffff;

    fwrite(&v, sizeof(v), 1, fp);
}

static void
output_unit_bitmask(FILE *fp, const struct rle *rle)
{
    struct rle_bitmask v;

    v.bit = !!rle->color;

    if (rle->length & ~0xeffff)
        fprintf(stderr,
                "ERROR: rle.length (%d) is too big for bitmask!\n",
                rle->length);

    v.length = rle->length & 0xefff;

    fwrite(&v, sizeof(v), 1, fp);
}

static void
output_unit_tinybitmask(FILE *fp, const struct rle *rle)
{
    struct rle_tinybitmask v;

    v.bit = !!rle->color;

    if (rle->length & ~0xef)
        fprintf(stderr,
                "ERROR: rle.length (%d) is too big for tiny-bitmask!\n",
            rle->length);

    v.length = rle->length & 0xef;

    fwrite(&v, sizeof(v), 1, fp);
}

static void
output_line_complete(output_unit_t output_unit, FILE *fp, const struct rle *rles, int rles_length)
{
    unsigned short v;
    int i;

    v = rles_length;
    fwrite(&v, sizeof(v), 1, fp);

    for (i = 0; i < rles_length; i++, rles++)
        output_unit(fp, rles);
}

static void
output_line_omit_white_end(output_unit_t output_unit, FILE *fp, const struct rle *rles, int rles_length)
{
    if (rles_length > 0) {
        if (rles[rles_length - 1].color == 0xffffff)
            rles_length--;
    }

    output_line_complete(output_unit, fp, rles, rles_length);
}

static void
output_line_omit_black_end(output_unit_t output_unit, FILE *fp, const struct rle *rles, int rles_length)
{
    if (rles_length > 0) {
        if (rles[rles_length - 1].color == 0x000000)
            rles_length--;
    }

    output_line_complete(output_unit, fp, rles, rles_length);
}


static int
encode(FILE *infile, FILE *outfile, output_line_t output_line, output_unit_t output_unit, rle_unit_type_t unit_type)
{
    int w, h, maxval, row, rles_length;
    int (*read_color)(FILE *, unsigned int *);
    struct rle *rles;

    if (parse_ppm(infile, &w, &h, &maxval) != 0)
        return -1;

    if (w < 1 || h < 1) {
        fputs("Invalid image dimensions.\n", stderr);
        return -1;
    }

    output_header(outfile, w, h, unit_type);

    if (maxval < 256)
        read_color = read_color_char;
    else
        read_color = read_color_short;

    rles = malloc(w * sizeof(struct rle));

    for (row = 0; row < h; row++) {
        struct rle last = {0, 0};
        int col;

        rles_length = 0;
        for (col = 0; col < w; col++) {
            unsigned int color;

            if (read_color(infile, &color) != 0) {
                fprintf(stderr, "File truncated at row %d, col %d\n", row, col);
                free(rles);
                return -1;
            }

            if (last.length != 0) {
                if (color == last.color)
                    last.length++;
                else {
                    rles[rles_length] = last;
                    rles_length++;
                    last.color = color;
                    last.length = 1;
                }
            } else {
                last.color = color;
                last.length = 1;
            }
        }
        rles[rles_length] = last;
        rles_length++;

        output_line(output_unit, outfile, rles, rles_length);
    }

    free(rles);
    return 0;
}

struct unit_mode {
    const char *name;
    output_unit_t func;
    rle_unit_type_t type;
};

struct line_mode {
    const char *name;
    output_line_t func;
};

static const struct line_mode line_modes[] = {
    {"complete", output_line_complete},
    {"omit_white_end", output_line_omit_white_end},
    {"omit_black_end", output_line_omit_black_end},
    {NULL, NULL}
};

static const struct unit_mode unit_modes[] = {
    {"color-rgb888", output_unit_color_rgb888, RLE_UNIT_TYPE_RGB888},
    {"color-rgb565", output_unit_color_rgb565, RLE_UNIT_TYPE_RGB565},
    {"grayscale", output_unit_grayscale, RLE_UNIT_TYPE_GRAYSCALE},
    {"bitmask", output_unit_bitmask, RLE_UNIT_TYPE_BITMASK},
    {"tiny-bitmask", output_unit_tinybitmask, RLE_UNIT_TYPE_TINY_BITMASK},
    {NULL, NULL}
};

static void
usage(const char *prg)
{
    const struct unit_mode *pu;
    const struct line_mode *pl;

    fprintf(stderr,
            "Usage:\n\n"
            "\t%s <unit-mode> <line-mode> <file.ppm> <outfile.dat>\n\n"
            "where <unit-mode> is one of:\n",
            prg);

    for (pu = unit_modes; pu->name != NULL; pu++)
        fprintf(stderr, "\t%s\n", pu->name);

    fputs("\nand <line-mode> is one of:\n", stderr);

    for (pl = line_modes; pl->name != NULL; pl++)
        fprintf(stderr, "\t%s\n", pl->name);

    fprintf(stderr, "\n");
}

static output_line_t
get_output_line(const char *mode)
{
    const struct line_mode *p;

    for (p = line_modes; p->name != NULL; p++)
        if (strcmp(p->name, mode) == 0)
            return p->func;

    return NULL;
}

static output_unit_t
get_output_unit(const char *mode, rle_unit_type_t *unit_type)
{
    const struct unit_mode *p;

    for (p = unit_modes; p->name != NULL; p++)
        if (strcmp(p->name, mode) == 0) {
            *unit_type = p->type;
            return p->func;
        }

    return NULL;
}

int
main(int argc, char *argv[])
{
    FILE *infile, *outfile;
    output_line_t output_line;
    output_unit_t output_unit;
    rle_unit_type_t unit_type;

    if (argc != 5) {
        usage(argv[0]);
        return -1;
    }

    output_unit = get_output_unit(argv[1], &unit_type);
    if (!output_unit) {
        usage(argv[0]);
        return -1;
    }

    output_line = get_output_line(argv[2]);
    if (!output_line) {
        usage(argv[0]);
        return -1;
    }

    infile = fopen(argv[3], "rb");
    if (!infile) {
        perror("fopen");
        return -1;
    }

    if (argv[4][0] == '-')
        outfile = stdout;
    else {
        outfile = fopen(argv[4], "wb");
        if (!outfile) {
            perror("fopen");
            fclose(infile);
            return -1;
        }
    }

    return encode(infile, outfile, output_line, output_unit, unit_type);
}
