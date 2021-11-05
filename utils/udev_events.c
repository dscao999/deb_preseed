#include <stdio.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <poll.h>
#include <errno.h>
#include <time.h>
#ifdef NDEBUG
#include <syslog.h>
#endif
#include <stdarg.h>
#include <getopt.h>
#include <signal.h>
#include <assert.h>
#include <sys/wait.h>

static volatile int global_exit = 0;
static volatile int child_exit = 0;

static void sighand(int sig)
{
	if (sig == SIGINT || sig == SIGTERM)
		global_exit = 1;
	else if (sig == SIGCHLD)
		child_exit = 1;
}

#ifdef NDEBUG
static inline void logerr(const char *fmt, ...)
{
	va_list ap;

	va_start(ap, fmt);
	vsyslog(LOG_INFO, fmt, ap);
	va_end(ap);
}
#else
static inline void logerr(const char *fmt, ...)
{
	va_list ap;

	va_start(ap, fmt);
	vfprintf(stderr, fmt, ap);
	fprintf(stderr, "\n");
	va_end(ap);
}
#endif

static int mkpipe(const char *pipe)
{
	int sysret, retv = -1;
	struct stat st;
	uid_t uid;
	gid_t gid;

	sysret = stat(pipe, &st);
	if (sysret == 0) {
		if ((st.st_mode & S_IFMT) != S_IFIFO ) {
			fprintf(stderr, "'%s' is not a fifo", pipe);
			goto exit_10;
		}
		uid = getuid();
		gid = getgid();	
		if ((uid != 0 || gid != 0) &&
				(st.st_uid != uid || st.st_gid != gid)) {
			fprintf(stderr, "'%s' is not ownd by you", pipe);
			goto exit_10;
		}
		if ((st.st_mode & (~S_IFMT)) != 0600) {
			fprintf(stderr, "'%s' mode is not 0600", pipe);
			goto exit_10;
		}
	} else {
		if (errno != ENOENT) {
			fprintf(stderr, "Cannot stat '%s': %s", pipe, strerror(errno));
			goto exit_10;
		}
		sysret = mknod(pipe, 0600|S_IFIFO, 0);
		if (sysret == -1) {
			fprintf(stderr, "Cannot mkpipe '%s': %s", pipe, strerror(errno));
			goto exit_10;
		}
	}

	retv = 0;

exit_10:
	return retv;
}

static void send_info(const char *pipe)
{
	const char *keyboard, *devpath;
	int fd, sysret;

#ifdef NDEBUG
	openlog("Set Keyboard", 0, 0);
#endif
	keyboard = getenv("ID_INPUT_KEYBOARD");
	if (keyboard == NULL || keyboard[0] != '1')
		return;
	fd = open(pipe, O_WRONLY|O_NONBLOCK);
	if (fd == -1) {
		if (errno != ENOENT)
			logerr("Cannot open pipe '%s'", pipe);
		return;
	}
	devpath = getenv("DEVPATH");
	if (devpath == NULL) {
		logerr("ID_INPUT_KEYBOARD without DEVPATH");
		goto exit_10;
	}
	sysret = write(fd, devpath, strlen(devpath));
	if (sysret == -1)
		logerr("Write to '%s' failed", pipe);
exit_10:
	close(fd);
#ifdef NDEBUG
	closenlog();
#endif
}

static void xset_keyboard(void)
{
	pid_t child;
	int sysret;

	child = fork();
	if (child == -1)
		fprintf(stderr, "Cannot fork: %s\n", strerror(errno));
	else if (child == 0) {
		static const struct timespec itv = {.tv_sec = 0, .tv_nsec = 200000000};
		nanosleep(&itv, NULL);
		sysret = execl("/usr/bin/setxkbmap", "setxkbmap", "-option",
				"srvrkeys:none", NULL);
		if (sysret == -1)
			fprintf(stderr, "execl failed: %s\n", strerror(errno));
		exit(1);
	}
}

static int recv_info(const char *pipe)
{
	struct pollfd pfd;
	int fd, retv, sysret, peer_exit;
	char buf[256];
	const char *slash;

	do {
		retv = 0;
		fd = open(pipe, O_RDONLY|O_NONBLOCK);
		if (fd == -1) {
			fprintf(stderr, "Cannot open '%s' for reading: %s\n",
					pipe, strerror(errno));
			return 2;
		}
		pfd.fd = fd;
		pfd.events = POLLIN;
		peer_exit = 0;
		do {
			if (child_exit) {
				child_exit = 0;
				waitpid(-1, NULL, WNOHANG);
			}
			pfd.revents = 0;
			sysret = poll(&pfd, 1, 500);
			if (sysret == -1 && errno != EINTR) {
				fprintf(stderr, "poll on '%s' failed: %s\n",
						pipe, strerror(errno));
				break;
			} else if (sysret == 0)
				continue;
			if ((pfd.revents & POLLHUP))
				peer_exit = 1;
			if (!(pfd.revents & POLLIN))
				continue;
			sysret = read(fd, buf, sizeof(buf));
			if (sysret == -1) {
				fprintf(stderr, "Read from '%s' failed: %s\n",
						pipe, strerror(errno));
				retv = 4;
				break;
			} else if (sysret == 0) {
				fprintf(stderr, "Read 0 bytes from pipe '%s'\n",
						pipe);
				continue;
			}
			buf[sysret] = 0;
			slash =strrchr(buf, '/');
			if (slash && strstr(slash+1, "event"))
				xset_keyboard();
		} while (!peer_exit && global_exit == 0);
		close(fd);
	} while (global_exit == 0);
	return retv;
}

int main(int argc, char *argv[])
{
	int fin, sndrcv, retv;
	const char *pipe = NULL;
	extern char *optarg;
	extern int optind, opterr, optopt;
	int lidx, opt;
	static const struct option lopt[] = {
		{"pipe", 1, NULL, 'p'},
		{"send", 0, NULL, 's'},
		{"recv", 0, NULL, 'r'},
		{}
	};
	struct sigaction sact;
	sigset_t mset;

	opterr = 0;
	sndrcv = 0;
	fin = 0;
	do {
		opt = getopt_long(argc, argv, ":srp:", lopt, &lidx);
		switch(opt) {
		case -1:
			fin = 1;
			break;
		case 's':
			sndrcv = 1;
			break;
		case 'r':
			sndrcv = 0;
			break;
		case 'p':
			pipe = optarg;
			break;
		case '?':
			fprintf(stderr, "Unknown option: %c\n", optopt);
			break;
		case ':':
			fprintf(stderr, "Missing argument for %c\n", optopt);
			break;
		default:
			assert(0);
		}
	} while (fin == 0);
	if (!pipe)
		pipe = "/tmp/keyboard-set";

	retv = 0;
	if (sndrcv == 1)
		send_info(pipe);
	else {
		if (mkpipe(pipe) == -1)
			return 1;
		sigemptyset(&mset);
		sact.sa_handler = sighand;
		sact.sa_mask = mset;
		sact.sa_flags = 0;
		if (sigaction(SIGINT, &sact, NULL) == -1)
			fprintf(stderr, "signal install failed: %s\n",
					strerror(errno));
		if (sigaction(SIGTERM, &sact, NULL) == -1)
			fprintf(stderr, "signal install failed: %s\n",
					strerror(errno));
		sact.sa_flags = SA_NOCLDWAIT;
		if (sigaction(SIGCHLD, &sact, NULL) == -1)
			fprintf(stderr, "signal install failed for SIGCHLD: " \
					"%s\n", strerror(errno));
		retv = recv_info(pipe);
		unlink(pipe);
	}
	return retv;
}
