CFLAGS += -Wall -Werror -std=c99

BINS = test-marshaller-string-array

.PHONY: all clean

test-marshaller-string-array: test-marshaller-string-array.c marshaller-string-array.c

all: $(BINS)

clean:
	rm -f $(BINS)

clean-bkps:
	rm -f *~
