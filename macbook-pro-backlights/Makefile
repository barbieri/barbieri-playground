STRIP = strip
CFLAGS += -O2 -Wall -Wextra -fdata-sections -ffunction-sections -Wl,--as-needed -Wl,--gc-sections

.PHONY: all clean

all: macbook-pro-kbd-baclkight macbook-pro-lvds-baclkight

macbook-pro-kbd-baclkight: macbook-pro-backlight-common.c
	$(CC) $^ -o $@ $(CFLAGS) \
		-DDEV_VAL='"/sys/class/leds/smc::kbd_backlight/brightness"' \
		-DDEV_MAX='"/sys/class/leds/smc::kbd_backlight/max_brightness"'
	$(STRIP) -s $@
	sudo chown root:root $@
	sudo chmod +s $@

macbook-pro-lvds-baclkight: macbook-pro-backlight-common.c
	$(CC) $^ -o $@ $(CFLAGS) \
		-DDEV_VAL='"/sys/class/backlight/apple_backlight/brightness"' \
		-DDEV_MAX='"/sys/class/backlight/apple_backlight/max_brightness"'
	$(STRIP) -s $@
	sudo chown root:root $@
	sudo chmod +s $@

clean:
	rm -f macbook-pro-kbd-baclkight macbook-pro-lvds-baclkight

