CC = gcc
RM = rm -f

GLIB_LDFLAGS := $$(pkg-config --libs glib-2.0)
GLIB_CFLAGS := $$(pkg-config --cflags glib-2.0)

LDFLAGS += \
	$(GLIB_LDFLAGS)

CFLAGS += \
	-Werror -Wformat -std=c99 -ansi  -D_XOPEN_SOURCE=600 \
	$(GLIB_CFLAGS)

utils_SOURCES = utils.c
utils_OBJECTS = $(patsubst %.c,%.o,$(utils_SOURCES))

.PHONY: all
all: liburl-path-utils.so

liburl-path-utils.so: $(utils_OBJECTS)
	$(CC) $(LDFLAGS) -shared $(utils_OBJECTS) -o $@


%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

test: liburl-path-utils.so test.o
	$(CC) $(LDFLAGS) -L. -Wl,-rpath=. \
		-lurl-path-utils \
		test.o -o $@

.PHONY: clean
clean:
	$(RM) $(utils_OBJECTS)
	$(RM) test
	$(RM) test.o
	$(RM) liburl-path-utils.so