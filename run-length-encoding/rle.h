#ifndef __RLE_H__
#define __RLE_H__ 1

typedef enum
{
    RLE_UNIT_TYPE_RGB888,
    RLE_UNIT_TYPE_RGB565,
    RLE_UNIT_TYPE_GRAYSCALE,
    RLE_UNIT_TYPE_BITMASK,
    RLE_UNIT_TYPE_TINY_BITMASK
} rle_unit_type_t;

struct rle_color_rgb888
{
    unsigned int color;
    unsigned int length;
};

struct rle_color_rgb565
{
    unsigned short color;
    unsigned short length;
};

struct rle_grayscale
{
    unsigned int level : 8;
    unsigned int length : 24;
};

struct rle_bitmask
{
    unsigned short bit : 1;
    unsigned short length : 15;
};

struct rle_tinybitmask
{
    unsigned char bit : 1;
    unsigned char length : 7;
};

#endif /* __RLE_H__ */

