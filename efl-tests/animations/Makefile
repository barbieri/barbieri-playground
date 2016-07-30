.PHONY: run clean all

THEMES= default.edj \
	light.edj \
	text.edj

BINS= \
	ball \
	fade \
	scale \
	ball-scale-fade

BUILT=$(THEMES) $(BINS)
CFLAGS=-g -Wall -std=c99 -D_XOPEN_SOURCE=600 \
	`pkg-config --cflags ecore edje`

LDFLAGS=`pkg-config --libs ecore edje`

all: $(BUILT)

%.edj: %.edc
	edje_cc $< $@

clean:
	rm -f *~ $(BUILT)
