#define _GNU_SOURCE
#include <sys/select.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <termios.h>
#include <unistd.h>
#include <stdio.h>
#include <errno.h>
#include <string.h>
#include <sys/un.h>
#include <stdlib.h>
#include <time.h>

char *default_socket_file_="/var/run/powersensordaemon/cmd.sock";
char *rrd_temp_ = "/home/sensortemp.rrd";
char *rrd_light_ = "/home/sensorlight.rrd";
char *rrd_movement_ = "/home/sensormovement.rrd";
const int sample_interval_s_ = 30;