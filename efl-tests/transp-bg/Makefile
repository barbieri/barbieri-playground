.PHONY: all clean

RESULT = test-transp-bg test.edj

all: $(RESULT)

EDJE_CC = edje_cc

test.edj: test.edc
	$(EDJE_CC) $<

test-transp-bg: test-transp-bg.c
	$(CC) $(CFLAGS) `pkg-config --libs --cflags evas ecore ecore-evas edje` $< -o $@


clean:
	$(RM) -f $(RESULT) *~
