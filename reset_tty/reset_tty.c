#include <stdlib.h>
#include <termios.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <time.h>
#include <stdio.h>
#include <sys/select.h>

#define STATE_OFF 0
#define STATE_ON  1

void setDTRState (int fd, int state) {
  int flags;

  ioctl(fd, TIOCMGET, &flags);
  flags = (state == STATE_ON ? flags | TIOCM_DTR : flags & ~TIOCM_DTR);
  ioctl(fd, TIOCMSET, &flags);
}

int
main(int argc, char* argv[])
{
  char* device = argc < 2 ? "/dev/ttyUSB0" : argv[1];
  int fd = open(device, O_RDWR);
  if (fd == 0) {
    fprintf(stderr, "Could not open %s\n", device);
    return EXIT_FAILURE;
  }
  
  setDTRState(fd, STATE_ON);
  struct timeval sleeptime = {0, 100000}; // 100ms
  select(0, NULL, NULL, NULL, &sleeptime);
  setDTRState(fd, STATE_OFF);
  sleeptime.tv_sec = 0;
  sleeptime.tv_usec = 100000;
  select(0, NULL, NULL, NULL, &sleeptime);
  setDTRState(fd, STATE_ON);
  close(fd);

  return EXIT_SUCCESS;
}

