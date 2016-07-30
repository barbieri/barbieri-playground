CFLAGS = `pkg-config --cflags edje`
LDFLAGS = `pkg-config --libs edje`

BUILT = edje_exec edje_template $(patsubst %.edc, %.edj, $(wildcard *.edc))

.PHONY: all clean

all: $(BUILT)

clean:
	rm -f *~ *.o $(BUILT)

%.edj: %.edc
	edje_cc $< $@
