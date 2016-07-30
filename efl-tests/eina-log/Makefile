.PHONY: all clean

all: eina-log-journal eina-log-simple eina-log-simple-domain eina-log-syslog

clean:
	rm -f eina-log-journal
	rm -f eina-log-simple
	rm -f eina-log-simple-domain
	rm -f eina-log-syslog

eina-log-journal: eina-log-journal.c
	$(CC) $(CFLAGS) $(LDFLAGS) \
		`pkg-config --cflags --libs eina libsystemd-journal` \
		$< -o $@

eina-log-simple: eina-log-simple.c
	$(CC) $(CFLAGS) $(LDFLAGS) \
		`pkg-config --cflags --libs eina` \
		$< -o $@

eina-log-simple-domain: eina-log-simple-domain.c
	$(CC) $(CFLAGS) $(LDFLAGS) \
		`pkg-config --cflags --libs eina` \
		$< -o $@

eina-log-syslog: eina-log-syslog.c
	$(CC) $(CFLAGS) $(LDFLAGS) \
		`pkg-config --cflags --libs eina` \
		$< -o $@

