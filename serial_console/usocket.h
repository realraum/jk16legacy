#include <sys/types.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <termios.h>
#include <unistd.h>
#include <stdio.h>
#include <errno.h>
#include <string.h>
#include <sys/select.h>
#include <sys/un.h>

char *default_socket_file_="/var/run/powersensordaemon/cmd.sock";
int quit_on_eof_ = 1;