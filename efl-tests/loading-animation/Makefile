.PHONY: run clean all

all: app

%.edj: %.edc
	edje_cc $< $@

app: app.c
	gcc \
	`pkg-config --cflags --libs edje ecore` \
	$< -o $@

clean:
	rm -f *~ app default.edj

run: app default.edj
	./app
