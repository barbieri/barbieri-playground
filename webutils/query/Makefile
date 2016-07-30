CC = gcc
RM = rm -f

GLIB_LDFLAGS := $$(pkg-config --libs glib-2.0)
GLIB_CFLAGS := $$(pkg-config --cflags glib-2.0)

LDFLAGS += \
	$(GLIB_LDFLAGS)

CFLAGS += \
	-Werror -Wformat -std=c99 -ansi -D_XOPEN_SOURCE=600 \
	$(GLIB_CFLAGS)

parser_SOURCES = parser.c
serializer_SOURCES = serializer.c

parser_OBJECTS = $(patsubst %.c,%.o,$(parser_SOURCES))
serializer_OBJECTS = $(patsubst %.c,%.o,$(serializer_SOURCES))

.PHONY: all
all: liburl-query-parser.so liburl-query-serializer.so test

liburl-query-parser.so: $(parser_OBJECTS)
	$(CC) $(LDFLAGS) -shared $(parser_OBJECTS) -o $@

liburl-query-serializer.so: $(serializer_OBJECTS)
	$(CC) $(LDFLAGS) -shared $(serializer_OBJECTS) -o $@


%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

test: liburl-query-parser.so liburl-query-serializer.so test.o
	$(CC) $(LDFLAGS) -L. -Wl,-rpath=. \
		-lurl-query-parser \
		-lurl-query-serializer \
		test.o -o $@

.PHONY: clean
clean:
	$(RM) $(parser_OBJECTS)
	$(RM) $(serializer_OBJECTS)
	$(RM) test
	$(RM) test.o
	$(RM) liburl-query-parser.so
