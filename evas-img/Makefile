.PHONY: clean all

CFLAGS = -O2 -Wall -Wextra -Wl,--as-needed -fdata-sections -ffunction-sections -Wl,--gc-sections

all: evas-img-resizer evas-img-viewer

clean:
	rm -f evas-img-resizer evas-img-viewer

evas-img-resizer: evas-img-resizer.c Makefile
	$(CC) $(CFLAGS) $< `pkg-config --cflags --libs evas ecore-evas` -o $@

evas-img-viewer: evas-img-viewer.c Makefile
	$(CC) $(CFLAGS) $< `pkg-config --cflags --libs evas ecore ecore-evas` -o $@
