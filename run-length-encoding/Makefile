.PHONY: all clean dist-clean strip

BINS = encoder sdl-viewer-fread sdl-viewer-mmap
CFLAGS = -Wall -Werror -std=c99 -O2 -I.
Q=@

all: $(BINS)

clean:
	rm -f $(BINS)

dist-clean: clean
	rm -f *~

%: %.c
	@echo -e "\t[CC] $@ \t<= $^"
	$(Q)$(CC) \
		$(CFLAGS) \
		$(LDFLAGS) \
		$^ -o $@

sdl-viewer-%: sdl-viewer-%.c sdl-viewer.c
	@echo -e "\t[CC] $@ \t<= $^"
	$(Q)$(CC) \
		$(CFLAGS) `sdl-config --cflags` \
		$(LDFLAGS) `sdl-config --libs` \
		$^ -o $@

strip: $(BINS)
	strip -s $(BINS)

