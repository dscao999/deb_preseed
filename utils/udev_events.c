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
#include <syslog.h>
#include <stdarg.h>
#include <getopt.h>
#include <signal.h>
#include <assert.h>
#include <sys/wait.h>

static volatile int global_exit = 0;
static volatile int child_exit = 0;
static int verbose = 0;

static void sighand(int sig)
{
	if (sig == SIGINT || sig == SIGTERM)
		global_exit = 1;
	else if (sig == SIGCHLD)
		child_exit = 1;
}

#define logerr(fmt, ...) syslog(LOG_ERR, fmt, __VA_ARGS__)
#define prterr(fmt, ...) fprintf(stderr, fmt, __VA_ARGS__)

static int mkpipe(const char *pipe)
{
	int sysret, retv = -1;
	struct stat st;
	uid_t uid;
	gid_t gid;

	sysret = stat(pipe, &st);
	if (sysret == 0) {
		if ((st.st_mode & S_IFMT) != S_IFIFO ) {
			prterr("'%s' is not a fifo", pipe);
			goto exit_10;
		}
		uid = getuid();
		gid = getgid();	
		if ((uid != 0 || gid != 0) &&
				(st.st_uid != uid || st.st_gid != gid)) {
			prterr("'%s' is not ownd by you", pipe);
			goto exit_10;
		}
		if ((st.st_mode & (~S_IFMT)) != 0600) {
			prterr("'%s' mode is not 0600", pipe);
			goto exit_10;
		}
	} else {
		if (errno != ENOENT) {
			prterr("Cannot stat '%s': %s", pipe, strerror(errno));
			goto exit_10;
		}
		sysret = mknod(pipe, 0600|S_IFIFO, 0);
		if (sysret == -1) {
			prterr("Cannot mkpipe '%s': %s", pipe, strerror(errno));
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
	int fd, sysret, cnt;
	struct stat pst;
	static const struct timespec itv = {.tv_sec = 0, .tv_nsec = 40000000};

	keyboard = getenv("ID_INPUT_KEYBOARD");
	if (keyboard == NULL || keyboard[0] != '1')
		return;
	openlog(NULL, 0, 0);
	devpath = getenv("DEVPATH");
	if (devpath == NULL)
		return;

	sysret = stat(pipe, &pst);
	if (sysret == -1) {
		if (errno != ENOENT)
			logerr("Cannot stat pipe '%s': %s", pipe,
					strerror(errno));
		return;
	}
	cnt = 0;
	fd = open(pipe, O_WRONLY|O_NONBLOCK);
	while (fd == -1 && cnt < 5) {
		nanosleep(&itv, 0);
		fd = open(pipe, O_WRONLY|O_NONBLOCK);
		cnt += 1;
	}
	if (fd == -1) {
		logerr("Cannot open pipe '%s'", pipe);
		return;
	}
	sysret = write(fd, devpath, strlen(devpath));
	if (sysret == -1)
		logerr("Write to '%s' failed", pipe);
	else if (verbose == 1)
		logerr("Send %d bytes to %s\n", sysret, pipe);

	close(fd);
	closelog();
}

static void execute_set()
{
	pid_t subpid;
	struct timespec itv;
	int sysret;

	subpid = fork();
	if (subpid == -1) {
		prterr("agent fork failed: %s\n", strerror(errno));
		return;
	} else if (subpid == 0) {
		if (verbose == 1) {
			clock_gettime(CLOCK_MONOTONIC_COARSE, &itv);
			prterr("[%6ld.%06ld] execute setxkbmap -option " \
					"srvrkeys:none\n",
					itv.tv_sec, (itv.tv_nsec)/1000);
		}
		sysret = execl("/usr/bin/setxkbmap", "setxkbmap", "-option",
				"srvrkeys:none", NULL);
		if (sysret == -1) {
			prterr("execl failed: %s\n", strerror(errno));
			exit(1);
		}
	}
}

static void xset_keyboard(int delay)
{
	pid_t child;
	int sysret;
	struct timespec itv, rem;
	itv.tv_sec = 0;
	itv.tv_nsec = (delay * 1000000ul);

	printf("tv_nsec: %ld\n", itv.tv_nsec);
	child = fork();
	if (child == -1)
		prterr("Cannot fork: %s\n", strerror(errno));
	else if (child == 0) {
		execute_set();
		do {
			sysret = nanosleep(&itv, &rem);
			itv = rem;
		} while (sysret == -1 && errno == EINTR);
		execute_set();
		exit(0);
	}
}

static int recv_info(const char *pipe, int delay)
{
	struct pollfd pfd;
	int fd, retv, sysret, peer_exit;
	char buf[256];
	const char *slash;

	do {
		retv = 0;
		do {
			fd = open(pipe, O_RDONLY);
			if (fd == -1 && errno != EINTR) {
				prterr("Cannot open '%s' for " \
						"reading: %s\n", pipe,
						strerror(errno));
				return 2;
			}
		} while (fd == -1 && global_exit == 0);
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
				prterr("poll on '%s' failed: %s\n",
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
				prterr("Read from '%s' failed: %s\n",
						pipe, strerror(errno));
				retv = 4;
				break;
			} else if (sysret == 0) {
				prterr("Read 0 bytes from pipe '%s'\n",
						pipe);
				continue;
			}
			buf[sysret] = 0;
			slash =strrchr(buf, '/');
			if (slash && strstr(slash+1, "event"))
				xset_keyboard(delay);
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
	int lidx, opt, delay;
	static const struct option lopt[] = {
		{"pipe", 1, NULL, 'p'},
		{"delay", 1, NULL, 'd'},
		{"send", 0, NULL, 's'},
		{"recv", 0, NULL, 'r'},
		{"verbose", 0, NULL, 'v'},
		{}
	};
	struct sigaction sact;
	sigset_t mset;
	struct timespec itv;

	opterr = 0;
	sndrcv = 0;
	fin = 0;
	delay = 300;
	do {
		opt = getopt_long(argc, argv, ":srvp:d:", lopt, &lidx);
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
		case 'd':
			delay = atoi(optarg);
			if (delay < 0) {
				delay = 300;
				prterr("Invalid delay %d, set to " \
						"150 milliseconds\n", delay);
			}
			if (delay > 1000) {
				delay = 300;
				prterr("More than one second, " \
						"truncated to %d\n", delay);
			}
			break;
		case 'v':
			verbose = 1;
			break;
		case '?':
			prterr("Unknown option: %c\n", optopt);
			break;
		case ':':
			prterr("Missing argument for %c\n", optopt);
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
			prterr("signal install failed for SIGINT: " \
					"%s\n", strerror(errno));
		if (sigaction(SIGTERM, &sact, NULL) == -1)
			prterr("signal install failed for SIGTERM: " \
					"%s\n", strerror(errno));
		sact.sa_flags = SA_NOCLDWAIT;
		if (sigaction(SIGCHLD, &sact, NULL) == -1)
			prterr("signal install failed for SIGCHLD: " \
					"%s\n", strerror(errno));
		clock_gettime(CLOCK_MONOTONIC_COARSE, &itv);
		printf("[%6ld.%06ld] %s: Ready for keyboard events.\n",
				itv.tv_sec, itv.tv_nsec / 1000, argv[0]);
		retv = recv_info(pipe, delay);
		unlink(pipe);
	}
	return retv;
}
