.PHONY: run clean all

THEMES= \
	simple.edj \
	complete.edj

BINS=

BUILT=$(THEMES) $(BINS)
CFLAGS=-g -Wall -std=c99 -D_XOPEN_SOURCE=600 \
	`pkg-config --cflags edje ecore`

LDFLAGS= `pkg-config --libs edje ecore`

all: $(BUILT)

%.edj: %.edc
	edje_cc $< $@

clean:
	rm -f *~ $(BUILT)
