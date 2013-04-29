#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>
#include <string.h>

#define PAGE_SIZE sysconf(_SC_PAGESIZE)

#define KB 1024UL
#define MB (KB*KB)

int main(int argc, char **argv)
{
	long mb, bytes;
	void *addr, *p;
	pid_t pid;
        int status;

	if (argc < 2)
		fprintf(stderr, "usage: memhog <num-MB>\n"), exit(1);

	mb = atol(argv[1]), bytes = mb * MB;

	if ((addr = malloc(bytes)) == NULL)
		perror("malloc"), exit(1);

	for (p = addr; p < addr + bytes; p += PAGE_SIZE)
		memset(p, 1, PAGE_SIZE);

	pid = getpid();
	printf("pid=%d MB=%ld (%ld)\n", pid, mb, bytes);
	printf("Hit Ctrl-C or run 'kill %d' to quit.\n", pid);
        for (;;) {
                pid = fork();
                if (pid == 0) {
                        return 0;
                }
                wait(&status);
        }
	return 0;
}
