#include "serial.h"


int setup_tty(int fd)
{
  struct termios tmio;
  
  int ret = tcgetattr(fd, &tmio);
  if(ret) {
    fprintf(stderr, "Error on tcgetattr(): %s", strerror(errno));
    return ret;
  }

  ret = cfsetospeed(&tmio, B9600);
  if(ret) {
    fprintf(stderr, "Error on cfsetospeed(): %s", strerror(errno));
    return ret;
  }

  ret = cfsetispeed(&tmio, B9600);
  if(ret) {
    fprintf(stderr, "Error on cfsetispeed(): %s", strerror(errno));
    return ret;
  }

  tmio.c_lflag &= ~ECHO;

  ret = tcsetattr(fd, TCSANOW, &tmio);
  if(ret) {
    fprintf(stderr, "Error on tcsetattr(): %s", strerror(errno));
    return ret;
  }
  
  ret = tcflush(fd, TCIFLUSH);
  if(ret) {
    fprintf(stderr, "Error on tcflush(): %s", strerror(errno));
    return ret;
  }

  fd_set fds;
  struct timeval tv;
  FD_ZERO(&fds);
  FD_SET(fd, &fds);
  tv.tv_sec = 0;
  tv.tv_usec = 50000;
  for(;;) {
    ret = select(fd+1, &fds, NULL, NULL, &tv);
    if(ret > 0) {
      char buffer[100];
      ret = read(fd, buffer, sizeof(buffer));
    }
    else
      break;
  }

  return 0;
}


int set_tty_raw(int fd, struct termios *termios_prev)
{
  struct termios tmio;
  
  int ret = tcgetattr(fd, &tmio);
  if(ret) {
    fprintf(stderr, "Error on tcgetattr(): %s", strerror(errno));
    return ret;
  }
  
  memcpy(termios_prev, &tmio,sizeof(struct termios));
  
  cfmakeraw(&tmio);
  
  ret = tcsetattr(fd, TCSANOW, &tmio);
  if(ret) {
    fprintf(stderr, "Error on tcsetattr(): %s", strerror(errno));
    return ret;
  }  
  
  fcntl(STDIN_FILENO, F_SETFL, O_NONBLOCK);
  
  return 0;
}

int restore_tty(int fd, struct termios  *termios_prev)
{
  int ret = tcsetattr(fd, TCSANOW, termios_prev);
  if(ret) {
    fprintf(stderr, "Error on tcsetattr(): %s", strerror(errno));
  }
  return ret;  
}

void  connect_terminal(int door_fd)
{
  if (door_fd < 3)
    return;
  fd_set fds_r;
  char buffer[256];
  int num_byte=0;
  FD_ZERO(&fds_r);

  FD_SET(STDIN_FILENO,&fds_r);
  FD_SET(door_fd,&fds_r);
  while (select(door_fd+1,&fds_r,0,0,0) > 0)
  {
    if (FD_ISSET(door_fd,&fds_r))
    {
      if ((num_byte = read(door_fd,buffer, 1)) > 0)
      {
        write(STDOUT_FILENO,buffer,num_byte);
      }
      if (num_byte == 0 || (num_byte <0 && errno != EAGAIN))
        return;
    }    
    if (FD_ISSET(STDIN_FILENO,&fds_r))
    {
      while((num_byte = read(STDIN_FILENO,buffer, 256)) > 0)
      {
        write(door_fd,buffer,num_byte);
      }
      if (num_byte <0 && errno != EAGAIN)
        return;
    }
    
    FD_SET(STDIN_FILENO,&fds_r);
    FD_SET(door_fd,&fds_r);
  }
}

int main(int argc, char* argv[])
{
  int ret = 0;
  int door_fd = 0;
  struct termios tmio_prev;
  
  if (argc > 0)
    door_dev_ = argv[1];
  
  for(;;) 
  {
    door_fd = open(door_dev_, O_RDWR | O_NONBLOCK); // | O_NOCTTY
    if(door_fd < 0)
      ret = 2;
    else {
      ret = setup_tty(door_fd);
      if(ret)
        ret = 2;
      else
      {
        ret = set_tty_raw(STDIN_FILENO,&tmio_prev);
        if (ret)
          break;
        
        connect_terminal(door_fd);
        
        ret = restore_tty(STDIN_FILENO,&tmio_prev);
        if (ret)
          break;        
      }
    }

    if (ret == 2) {
      fprintf(stderr, "%s error, trying to reopen in 5 seconds..", door_dev_);
      if(door_fd > 0)
        close(door_fd);
      sleep(5);
    }
    else
      break;
  }

  if(door_fd > 0)
    close(door_fd);
  return(ret);
}

