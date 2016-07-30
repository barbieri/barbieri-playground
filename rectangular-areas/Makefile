.PHONY: all clean

BUILT = rect_splitter_test
CFLAGS += -Wall -Wextra -Wno-unused-parameter -Wformat-security -Winline -g \
	  `sdl-config --cflags`
LDFLAGS += `sdl-config --libs`

ifneq ($(NOOPTIMIZE),1)
CFLAGS+= -O2  -Wuninitialized
endif

ifeq ($(DEBUG),1)
CFLAGS += -D_FORTIFY_SOURCE=2
else
CFLAGS += -DNDEBUG=1
endif

rect_splitter_test: rect_splitter_test.c rect_splitter.c



all: $(BUILT)

clean:
	rm -f *.o $(BUILT)
