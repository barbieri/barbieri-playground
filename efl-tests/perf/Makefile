.PHONY: run clean all

BINS= \
	mover \
	alpha \
	multi-mover

THEMES= \
	default.edj

BUILT=$(BINS) $(THEMES)

ARCH:=$(shell arch)
CFLAGS+= -Wall -Werror -Wextra \
	 -Wno-unused-parameter -Wformat-security \
	 -std=c99 -D_XOPEN_SOURCE=600 \
	`pkg-config --cflags --libs edje ecore`


ifeq ($(DEBUG),1)
CFLAGS+= -g -D_FORTIFY_SOURCE=2
else
CFLAGS+= -DNDEBUG=1
endif

ifeq ($(OPTIMIZE),1)
CFLAGS+= -O3  -Wuninitialized

ifeq ($(ARCH), arm)
CFLAGS+= -mfpu=vfp -mfloat-abi=softfp -mcpu=arm1136j-s
endif
endif

all: $(BUILT)

%.edj: %.edc
	edje_cc $< $@

clean:
	rm -f *~ $(BUILT)
