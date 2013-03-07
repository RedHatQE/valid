#include <unistd.h>
#include <sys/types.h>
#include <sys/wait.h>

int main(void)
{
        int status;
        pid_t pid; 
        for (;;) {
                pid = fork();
                if (pid == 0) {
                        return 0;
                }
                wait(&status);
        }
}
