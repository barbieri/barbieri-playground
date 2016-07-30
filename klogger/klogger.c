#include <stdio.h>
#include <string.h>

int main(int argc, char *argv[])
{
	FILE *f;
	int i;

	if (argc < 2) {
		fprintf(stderr, "Usage:\n\t%s <message>\n", argv[0]);
		return -1;
	}

	f = fopen("/dev/kmsg", "w");
	if (!f) {
		perror("could not open /dev/kmsg");
		return -1;
	}

	for (i = 1; i < argc;) {
		size_t len = strlen(argv[i]);
		fwrite(argv[i], len, 1, f);
		i++;
		if (i < argc)
		  fputc(' ', f);
	}
	fputc('\n', f);
	fclose(f);
	return 0;
}
