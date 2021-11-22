#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <errno.h>
#include <signal.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>

int main(int argc, char *argv[])
{
	int retv = 0, nbytes, buflen, sysret, len;
	char *buf;
	int psum[2], psumout, psumin, fdin, fdout, fdtmp;
	struct sigaction mact;

	memset(&mact, 0, sizeof(mact));
	mact.sa_handler = SIG_DFL;
	mact.sa_flags = SA_NOCLDWAIT|SA_NOCLDSTOP;
	sigaction(SIGCHLD, &mact, NULL);
	sysret = pipe(psum);
	if (sysret == -1) {
		retv = 5;
		fprintf(stderr, "Cannot open pipe: %s\n", strerror(errno));
		return retv;
	}
	psumin = psum[0];
	psumout = psum[1];
	sysret = fork();
	if (sysret == -1) {
		retv = 6;
		fprintf(stderr, "Cannot fork: %s\n", strerror(errno));
		goto exit_10;
	} else if (sysret == 0) {
		/* child to do mdsum */
		close(psumout);
		fclose(stdin);
		fdin = dup(psumin);
		close(psumin);
		if (fdin == -1) {
			fprintf(stderr, "Cannot dup fd for stdin: %s\n",
					strerror(errno));
			exit(9);
		}
		stdin = fdopen(fdin, "rb");
		if (stdin == NULL) {
			fprintf(stderr, "Cannot reopen stdin in child: %s\n",
					strerror(errno));
			exit(10);
		}
		fdtmp = open("/tmp/md5sum.txt", O_WRONLY|O_CREAT, S_IRUSR|S_IWUSR|S_IRGRP|S_IROTH);
		if (fdtmp == -1) {
			fprintf(stderr, "Cannot open /tmp/md5sum.txt: %s\n",
					strerror(errno));
			exit(11);
		}
		fclose(stdout);
		fdout = dup(fdtmp);
		close(fdtmp);
		if (fdout == -1) {
			fprintf(stderr, "Cannot dup fd for stdout: %s\n",
					strerror(errno));
			exit(12);
		}
		stdout = fdopen(fdout, "wb");
		sysret = execlp("md5sum", "md5sum", "-b", NULL);
		fprintf(stderr, "Cannot exec md5sum: %s\n", strerror(errno));
		exit(13);
	}

	close(psumin);
	buflen = 16*1024;
	buf = malloc(buflen);
	nbytes = fread(buf, 1, buflen, stdin);
	while (nbytes > 0) {
		len = fwrite(buf, 1, nbytes, stdout);
		if (len != nbytes)
			fprintf(stderr, "Data written mismatch %d - %d\n",
					nbytes, len);
		len = write(psumout, buf, nbytes);
		if (len != nbytes) {
			fprintf(stderr, "Data written mismatch %d - %d\n",
					nbytes, len);
			if (len == -1) {
				fprintf(stderr, "Cannot write to pipe: %s\n",
						strerror(errno));
				break;
			}
		}
		nbytes = fread(buf, 1, buflen, stdin);
	}
	close(psumout);
	free(buf);

exit_10:
	close(psumin);
	close(psumout);
	return retv;
}
