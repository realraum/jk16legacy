#include "usocket.h"

void  connect_terminal(int fd)
{
  if (fd < 3)
    return;
  fd_set fds_r;
  char buffer[1024];
  int num_byte=0;
  char stdin_valid_fd=1;
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
    if (stdin_valid_fd && FD_ISSET(STDIN_FILENO,&fds_r))
    {
      while((num_byte = read(STDIN_FILENO,buffer, 1024)) > 0)
      {
        send(fd,buffer,num_byte,0);
      }
      if (num_byte <0 && errno != EAGAIN)
        return;
      if (num_byte == 0)
      {
        if (quit_on_eof_)
          return;
        else
        {
          stdin_valid_fd=0;
          FD_CLR(STDIN_FILENO,&fds_r);
        }
      }
    }
    
    FD_SET(fd,&fds_r);
    if (stdin_valid_fd)
      FD_SET(STDIN_FILENO,&fds_r);
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
    fprintf(stderr, "unable to connect to '%s': %s\n", local.sun_path, strerror(errno));
    return -1;
  }
  
  return fd;
}


int main(int argc, char* argv[])
{
  int ret = 0;
  int socket_fd = 0;
  char *socket_file;
  
  if (argc > 1)
    socket_file = argv[1];
  else
    socket_file = default_socket_file_;
  
  //give a second argument, to not quit on EOF on stdin.
  //useful if you just want to pipe some commands to usocket with echo and then listen to stdout
  if (argc > 2)
    quit_on_eof_=0;
  
  socket_fd = establish_socket_connection(socket_file);
  if(socket_fd)
  {
    fcntl(STDIN_FILENO, F_SETFL, O_NONBLOCK);
    connect_terminal(socket_fd);
  }
  else
  {
    fprintf(stderr, "%s error, aborting..\n", socket_file);
    ret=2;
  }

  if(socket_fd > 0)
    shutdown(socket_fd,SHUT_RDWR);
  return(ret);
}

