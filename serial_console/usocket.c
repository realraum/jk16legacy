#include "usocket.h"


int set_tty_raw(int fd, struct termios *termios_prev)
{
  struct termios tmio;
  
  int ret = tcgetattr(fd, &tmio);
  if(ret) {
    fprintf(stderr, "Error on tcgetattr(): %s\n", strerror(errno));
    return ret;
  }
  
  memcpy(termios_prev, &tmio,sizeof(struct termios));
  
  cfmakeraw(&tmio);
  
  ret = tcsetattr(fd, TCSANOW, &tmio);
  if(ret) {
    fprintf(stderr, "Error on tcsetattr(): %s\n", strerror(errno));
    return ret;
  }  
  
  fcntl(STDIN_FILENO, F_SETFL, O_NONBLOCK);
  
  return 0;
}

int restore_tty(int fd, struct termios  *termios_prev)
{
  int ret = tcsetattr(fd, TCSANOW, termios_prev);
  if(ret) {
    fprintf(stderr, "Error on tcsetattr(): %s\n", strerror(errno));
  }
  return ret;
}

void  connect_terminal(int fd)
{
  if (fd < 3)
    return;
  fd_set fds_r;
  char buffer[1024];
  int num_byte=0;
  FD_ZERO(&fds_r);

  FD_SET(STDIN_FILENO,&fds_r);
  FD_SET(fd,&fds_r);
  while (select(fd+1,&fds_r,0,0,0) > 0)
  {
    if (FD_ISSET(fd,&fds_r))
    {
      if ((num_byte = recv(fd,buffer, 1024,0)) > 0)
      {
        //~ printf("%d:%s\n",num_byte,buffer);
        write(STDOUT_FILENO,buffer,num_byte);
      }
      if (num_byte == 0 || (num_byte <0 && errno != EAGAIN))
        return;
    }    
    if (FD_ISSET(STDIN_FILENO,&fds_r))
    {
      while((num_byte = read(STDIN_FILENO,buffer, 1024)) > 0)
      {
        send(fd,buffer,num_byte,0);
      }
      if (num_byte <0 && errno != EAGAIN)
        return;
    }
    
    FD_SET(STDIN_FILENO,&fds_r);
    FD_SET(fd,&fds_r);
  }
}

int establish_socket_connection(const char* path)
{
  int fd = socket(AF_UNIX, SOCK_STREAM, 0);
  if(fd < 0) {
    fprintf(stderr, "unable to open socket: %s\n", strerror(errno));
    return -1;
  }

  struct sockaddr_un local;
  local.sun_family = AF_UNIX;
  if(sizeof(local.sun_path) <= strlen(path)) {
    fprintf(stderr, "socket path is to long (max %lu)\n", sizeof(local.sun_path)-1);
    return -1;
  }
  
  strcpy(local.sun_path, path);
  int len = SUN_LEN(&local);
  int ret = connect(fd, (struct sockaddr*) &local, len);
  if(ret) {
    fprintf(stderr, "unable to bind to '%s': %s\n", local.sun_path, strerror(errno));
    return -1;
  }
  
  return fd;
}


int main(int argc, char* argv[])
{
  int ret = 0;
  int socket_fd = 0;
  //~ struct termios tmio_prev;
  
  if (argc > 0)
    socket_file_ = argv[1];
  
  for(;;) 
  {
    socket_fd = establish_socket_connection(socket_file_);
    if(socket_fd < 0)
      ret = 2;
    else {
      //~ ret = set_tty_raw(STDIN_FILENO,&tmio_prev);
      //~ if (ret)
        //~ break;
      fcntl(STDIN_FILENO, F_SETFL, O_NONBLOCK);
      connect_terminal(socket_fd);
        
      //~ ret = restore_tty(STDIN_FILENO,&tmio_prev);
      //~ if (ret)
        //~ break;        
    }
    if (ret == 2) {
      fprintf(stderr, "%s error, trying to reopen in 5 seconds..\n", socket_file_);
      if(socket_fd > 0)
        shutdown(socket_fd,SHUT_RDWR);
      sleep(5);
    }
    else
      break;
  }

  if(socket_fd > 0)
    shutdown(socket_fd,SHUT_RDWR);
  return(ret);
}

