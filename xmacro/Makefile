VERSION=0.3
LDFLAGS = -Wl,--gc-sections -fno-strict-aliasing -Wl,--as-needed -Wl,--no-copy-dt-needed-entries -lrt
CFLAGS = -O2 -Wall -Wextra -pedantic -Wpointer-arith -Wno-missing-field-initializers -fvisibility=hidden -fdata-sections -ffunction-sections -O0 -ggdb3
#CFLAGS = -O0 -ggdb3 -Wall -Wextra -pedantic -Wpointer-arith -Wno-missing-field-initializers -fvisibility=hidden -fdata-sections -ffunction-sections


X_CFLAGS = $(shell pkg-config --cflags x11 xtst)
X_LIBS = $(shell pkg-config --libs x11 xtst)

.PHONY: all clean

BINS = xmacroplay xmacrorec

all: $(BINS)

clean:
	rm -f $(BINS)

xmacroplay: xmacroplay.cpp chartbl.h
	$(CXX) $(CFLAGS) $(X_CFLAGS) -DVERSION=$(VERSION) $^ $(LDFLAGS) -o $@ $(X_LIBS)

xmacrorec: xmacrorec.cpp
	$(CXX) $(CFLAGS) $(X_CFLAGS) -DVERSION=$(VERSION) $^ $(LDFLAGS) -o $@ $(X_LIBS)
