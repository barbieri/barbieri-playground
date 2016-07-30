#include <stdlib.h>
#include <string.h>
#include <alloca.h>
#include <stdio.h>

/**
 * @warning These functions just work on machines with the same pointer
 *          size and byte sex (endianess). They're mean to communicate
 *          between process on the same machine, but can be used on
 *          remote machines given these constraints. If you want to
 *          make it general purpose, then convert integers to network
 *          (Motorola, big endian) endianess and make the integers and
 *          pointers the largest possible (64bits?).
 */

/**
 * Serialize the string array.
 *
 * String is serialized using provided buffer, which might be reallocated
 * to fit. Serliazed format is:
 *
 *    [memory offsets|huge string that contains NULL delimited sub strings]
 *
 * memory offsets is an array of argc elements of size sizeof(char *) with
 * the offset in the huge string, since the first offset is always zero,
 * it's used to store @p argc.
 *
 * @param buflen current size of @p buf in bytes, on exit will contain new
 *        size if @p buf was resized. Should be 0 if @p buf is NULL.
 * @param buf buffer to operate on, might be NULL. Buffer will be resized if
 *        required and the new pointer is returned by the function.
 * @param reqlen required size of the buffer to serialize the array. Might
 *        be less or equal than @p bufflen. The memory area at the end of
 *        @p buf that is sized as the difference of @p buflen and
 *        @p reqlen is undefined and is not touched.
 * @param argc number of elements in @p argv.
 * @param argv string array to be serialized.
 *
 * @return pointer to buffer with serialized string array. Buffer size will
 *         be stored in @p buflen and serialized size in @p reqlen.
 */
char *
marshal_string_array(int *buflen, char *buf, int *reqlen, int argc, const char * const *argv)
{
        char **offsets, *p;
        int *sizes;
        int i, header_size;

        if (argc < 1) {
                *reqlen = 0;
                return buf;
        }

        header_size = sizeof(char *) * argc;
        *reqlen = header_size;
        sizes = alloca(sizeof(int) * argc);
        for (i = 0; i < argc; i++) {
                sizes[i] = strlen(argv[i]) + 1;
                *reqlen += sizes[i];
        }

        if (*buflen < *reqlen) {
                char *tmp;

                tmp = realloc(buf, *reqlen);
                if (!tmp) {
                        perror("realloc: failed to enlarge buffer");
                        *reqlen = 0;
                        return buf;
                }

                *buflen = *reqlen;
                buf = tmp;
        }

        offsets = (char **)buf;
        offsets[0] = (char *)0;
        for (i = 0; i < (argc - 1); i++)
                offsets[i + 1] = offsets[i] + sizes[i];
        offsets[0] = (char *)argc; /* first is always zero, store useful info */

        p = buf + header_size;
        for (i = 0; i < argc; p += sizes[i], i++)
                memcpy(p, argv[i], sizes[i]);

        return buf;
}

/**
 * Parse the serialized string array.
 *
 * The string is unparsed *IN PLACE* in given @p buf.
 *
 * @param buf buffer to operate on. It will be modified to contain the
 *        string array. Must not be NULL.
 * @param argc returns the number of elements in the string array.
 *
 * @return parsed string array. It's a single block of memory (actually
 *         it's the same as @p buf) and should be freed like it.
 */
char **
unmarshal_string_array(char *buf, int *argc)
{
        char **offsets;
        int i;

        offsets = (char **)buf;
        *argc = (int)offsets[0];
        offsets[0] = buf + sizeof(char *) * *argc;
        for (i = 1; i < *argc; i++)
                offsets[i] += (int)offsets[0];

        return offsets;
}
