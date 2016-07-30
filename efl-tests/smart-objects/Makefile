.PHONY: run clean all

BINS= \
	icon_viewer_simple \
	icon_viewer_edje \
	multiple_icon_viewer_edje

THEMES= \
	default.edj

BUILT=$(BINS) $(THEMES)

all: $(BUILT)

%.edj: %.edc
	edje_cc $< $@

icon_viewer_simple: icon_viewer.c icon_simple.c
	gcc -g -Wall -std=c99 -D_XOPEN_SOURCE=600 \
	`pkg-config --cflags --libs edje ecore` \
	$^ -o $@

icon_viewer_edje: icon_viewer.c icon_edje.c
	gcc -g -Wall -std=c99 -D_XOPEN_SOURCE=600 \
	`pkg-config --cflags --libs edje ecore` \
	$^ -o $@

multiple_icon_viewer_edje: multiple_icon_viewer.c icon_edje.c
	gcc -g -Wall -std=c99 -D_XOPEN_SOURCE=600 \
	`pkg-config --cflags --libs edje ecore` \
	$^ -o $@

clean:
	rm -f *~ $(BUILT)
