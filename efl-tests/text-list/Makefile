.PHONY: run clean all

BINS= \
	app \
	app2 \
	app3 \
	app4 \
	app5 \
	app6 \
	test-events

THEMES= \
	default.edj \
	light.edj

BUILT=$(BINS) $(THEMES)

ARCH:=$(shell arch)
CFLAGS+= -Wall -Werror -Wextra \
	 -Wno-unused-parameter -Wformat-security \
	 -std=c99 -D_XOPEN_SOURCE=600

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

%: %.c e_box.c key_monitor.c
	gcc $(CFLAGS) \
	`pkg-config --cflags --libs edje ecore` \
	$^ -o $@

app5: app5.c vlist.c key_monitor.c
	gcc $(CFLAGS) \
	`pkg-config --cflags --libs edje ecore` \
	$^ -o $@

app6: app6.c vlist.c key_monitor.c icon_edje.c
	gcc $(CFLAGS) \
	`pkg-config --cflags --libs edje ecore` \
	$^ -o $@

clean:
	rm -f *~ $(BUILT)
