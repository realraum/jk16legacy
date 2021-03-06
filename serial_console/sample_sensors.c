#include "sample_sensors.h"

int check_handle_line(char *buffer, unsigned int buflen, char *cmpstr, char *rrd_file, char *txt_file)
{
  char *cmd;
  unsigned int cmpstrlen = strlen(cmpstr);
  unsigned int value = atoi(buffer + cmpstrlen);
  if (buflen > cmpstrlen && strncmp(cmpstr,buffer,cmpstrlen) == 0)
  {
    if (asprintf(&cmd, "rrdtool update %s N:%d", rrd_file, value))
    {
      //printf("%s\n",cmd);
      system(cmd);
      free(cmd);
    }
    int fd = open(txt_file, O_WRONLY | O_CREAT | O_TRUNC, 0666);
    if (fd) 
    {
      if (asprintf(&cmd, "%d", value))
      {
        
        write(fd,cmd, strnlen(cmd,12)); //elim. newline
        free(cmd);
      }
      close(fd);
    }
    return 1;
  }
  return 0;
}

int check_handle_line_float(char *buffer, unsigned int buflen, char *cmpstr, char *rrd_file, char *txt_file)
{
  char *cmd;
  unsigned int cmpstrlen = strlen(cmpstr);
  float value = atof(buffer + cmpstrlen);
  if (buflen > cmpstrlen && strncmp(cmpstr,buffer,cmpstrlen) == 0)
  {
    if (asprintf(&cmd, "rrdtool update %s N:%f", rrd_file, value))
    {
      system(cmd);
      free(cmd);
    }
    int fd = open(txt_file, O_WRONLY | O_CREAT | O_TRUNC, 0666);
    if (fd) 
    {
      if (asprintf(&cmd, "%f", value))
      {
        
        write(fd,cmd, strnlen(cmd,12)); //elim. newline
        free(cmd);
      }
      close(fd);
    }
    return 1;
  }
  return 0;
}

unsigned int collect_data(char *buffer, unsigned int size)
{
  if (size >= 8 && strncmp("movement", buffer, 8) == 0)
    return 1;
  else if (check_handle_line_float(buffer, size, "temp0: ", rrd_temp_, txt_temp_))
    return 0;
  else if (check_handle_line(buffer, size, "photo0: ", rrd_light_, txt_light_))
    return 0;
  return 0;
}

void  sample_sensors(int fd)
{
  if (fd < 3)
    return;
  struct timeval timeout;
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
  timeout.tv_usec=0;
  last_sample_time=time(0);
  while (select(fd+1,&fds_r,0,0,&timeout) > -1)
  {
    curr_time=time(0);
    if (FD_ISSET(fd,&fds_r))
    {
      if ((num_byte = recv(fd, buffer+buffer_offset , buffer_size - buffer_offset ,0)) > 0)
      {
        buffer_offset+=num_byte;
      }
      
      if (num_byte < 1)
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
    timeout.tv_usec=0;
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
  int socket_fd = 0;
  char *socket_file;
  if (argc > 1)
    socket_file = argv[1];
  else
    socket_file = default_socket_file_;
  
  while (1)
  {
    socket_fd = establish_socket_connection(socket_file);
    if(socket_fd)
    {
      sample_sensors(socket_fd);
    }
    else
    {
      fprintf(stderr, "%s error, retrying..\n", socket_file);
    }

    if(socket_fd > 0)
      shutdown(socket_fd,SHUT_RDWR);
    
    sleep(2);
  }
  return 0;
}

