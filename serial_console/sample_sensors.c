#include "sample_sensors.h"

unsigned int collect_data(char *buffer, unsigned int size)
{
  char *cmd;
  if (size >= 8 && strncmp("movement", buffer, 8) == 0)
    return 1;
  
  if (size > 16 && strncmp("temp0:", buffer, 5) == 0)
  {
    if (asprintf(&cmd, "rrdtool update %s -t temp N:%s", rrd_temp_, buffer + 15))
    {
      /*printf("%s\n",cmd);*/
      system(cmd);
      free(cmd);
    }
  }
  
  if (size > 16 && strncmp("photo0:", buffer, 6) == 0)
  {
    if (asprintf(&cmd, "rrdtool update %s -t light N:%s", rrd_light_, buffer + 15))
    {
      /*printf("%s\n",cmd);*/
      system(cmd);
      free(cmd);
    }
  }
  return 0;  
}

void  sample_sensors(int fd)
{
  if (fd < 3)
    return;
  struct timespec timeout;
  fd_set fds_r;
  unsigned int const buffer_size=1024;
  unsigned int buffer_offset=0;
  char buffer[1024];
  char *cmd;
  unsigned int movement_count=0;
  int num_byte=0;
  time_t last_sample_time, curr_time;
  
  send(fd,"listen sensor\n",14,0);
  send(fd,"listen movement\n",16,0);
  
  FD_ZERO(&fds_r);
  FD_SET(fd,&fds_r);
  timeout.tv_sec=1;
  timeout.tv_nsec=0;
  last_sample_time=time(0);
  while (select(fd+1,&fds_r,0,0,0) > 0)
  {
    curr_time=time(0);
    if (FD_ISSET(fd,&fds_r))
    {
      if ((num_byte = recv(fd, buffer+buffer_offset , buffer_size - buffer_offset ,0)) > 0)
      {
        buffer_offset+=num_byte;
      }
      
      if (num_byte == 0 || (num_byte <0 && errno != EAGAIN))
        return;
      
      char linebreak_found=0;
      if (buffer_offset > 0)
      {
        do
        {
          int c=0;
          linebreak_found=0;
          for (c=0; c < buffer_offset; c++)
            if (buffer[c] == '\n')
            {
              buffer[c]='\0';
              linebreak_found=1;
              break;
            }
            
          if (linebreak_found)
          {
            movement_count += collect_data(buffer, buffer_offset+c);
            if (c < buffer_offset)
            {
              memmove(buffer, buffer + c + 1, buffer_size - c - 1);
            }
            buffer_offset -= c + 1;
          }
        } while (linebreak_found);
      }
      
    }
    
    if (curr_time - last_sample_time > sample_interval_s_)
    {
      last_sample_time=curr_time;
      if (asprintf(&cmd,"rrdtool update %s -t movement N:%d", rrd_movement_, movement_count))
      {
        /*printf("%s\n",cmd);*/
        system(cmd);
        free(cmd);
        movement_count=0;
      }
    }
    
    FD_SET(fd,&fds_r);
    timeout.tv_sec=1;
    timeout.tv_nsec=0;
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
  
  socket_fd = establish_socket_connection(socket_file);
  if(socket_fd)
  {
    sample_sensors(socket_fd);
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

