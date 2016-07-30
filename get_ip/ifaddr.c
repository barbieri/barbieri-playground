#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <sys/ioctl.h>
#include <net/if.h>
#include <netinet/in.h>
#include <arpa/inet.h>

int main(int argc, char *argv[])
{
	struct sockaddr_in *sin;
	struct ifreq ifr;
	int sk;

	if (argc != 2) {
		fprintf(stderr, "USAGE: %s <interface>\n", argv[0]);
		exit(1);
	}

	sk = socket(AF_INET, SOCK_DGRAM, 0);
	if (sk < 0) {
		perror("socket()");
		exit(1);
	}

	memset(&ifr, 0, sizeof(ifr));
	ifr.ifr_addr.sa_family = AF_INET;
	strncpy(ifr.ifr_name, argv[1], sizeof(ifr.ifr_name));

	if (ioctl(sk, SIOCGIFADDR, &ifr) < 0) {
		perror("ioctl()");
		exit(1);
	}

	sin = (struct sockaddr_in *)&ifr.ifr_addr;
	printf("IP: %s\n", inet_ntoa(sin->sin_addr));

	return 0;
}
