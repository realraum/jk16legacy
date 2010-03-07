/*
 *  powersensordaemon
 *
 *  Copyright (C) 2009 Christian Pointner <equinox@spreadspace.org>
 *
 *  This file is part of powersensordaemon.
 *
 *  powersensordaemon is free software: you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation, either version 3 of the License, or
 *  any later version.
 *
 *  powersensordaemon is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with powersensordaemon. If not, see <http://www.gnu.org/licenses/>.
 */

#include "datatypes.h"

#include <termios.h>
#include <unistd.h>

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>

#include <sys/un.h>

#include "log.h"
#include "sig_handler.h"
#include "options.h"

#include "command_queue.h"
#include "client_list.h"

#include "daemon.h"

#include "autosample.h"

int init_command_socket(const char* path)
{
  int fd = socket(AF_UNIX, SOCK_STREAM, 0);
  if(fd < 0) {
    log_printf(ERROR, "unable to open socket: %s", strerror(errno));
    return -1;
  }

  struct sockaddr_un local;
  local.sun_family = AF_UNIX;
  if(sizeof(local.sun_path) <= strlen(path)) {
    log_printf(ERROR, "socket path is to long (max %d)", sizeof(local.sun_path)-1);
    return -1;
  }
  strcpy(local.sun_path, path);
  unlink(local.sun_path);
  int len = SUN_LEN(&local);
  int ret = bind(fd, (struct sockaddr*)&local, len);
  if(ret) {
    log_printf(ERROR, "unable to bind to '%s': %s", local.sun_path, strerror(errno));
    return -1;
  }
  
  ret = listen(fd, 4);
  if(ret) {
    log_printf(ERROR, "unable to listen on command socket: %s", local.sun_path, strerror(errno));
    return -1;
  }

  log_printf(INFO, "now listening on %s for incoming commands", path);
  
  return fd;
}

void clear_fd(int fd)
{
  fd_set fds;
  struct timeval tv;
  FD_ZERO(&fds);
  FD_SET(fd, &fds);
  tv.tv_sec = 0;
  tv.tv_usec = 50000;
  for(;;) {
    int ret = select(fd+1, &fds, NULL, NULL, &tv);
    if(ret > 0) {
      char buffer[100];
      ret = read(fd, buffer, sizeof(buffer));
    }
    else
      break;
  }
}

int send_command(int tty_fd, cmd_t* cmd)
{
  if(!cmd)
    return -1;
  
  char c;
  switch(cmd->cmd) {
  case POWER_ON: {
    if(!cmd->param)
      return 0;
    c = toupper(cmd->param[0]);
    break;
  }
  case POWER_OFF: {
    if(!cmd->param)
      return 0;
    c = tolower(cmd->param[0]);
    break;
  }
  case SAMPLE: {
    if(!cmd->param)
      return 0;
    c = cmd->param[0];
    break;
  }
  default: return 0;
  }
  
  int ret;
  do {
    ret = write(tty_fd, &c, 1);
  } while(!ret || (ret == -1 && errno == EINTR));

  if(ret > 0) {
    cmd_sent(cmd);
    return 0;
  }

  return ret;
}

int send_response(int fd, const char* response)
{
  if(!response)
    return -1;

  int len = strlen(response);
  int offset = 0;
  int ret;
  for(;;) {
    ret = write(fd, &response[offset], len - offset);
    if(ret < 0) {
      if(errno != EINTR)
        return ret;

      ret = 0;
    }

    offset += ret;
    if(offset+1 >= len)
      break;
  }
  do {
    ret = write(fd, "\n", 1);
  } while(!ret || (ret == -1 && errno == EINTR));

  if(ret > 0)
    return 0;

  return ret;
}

#define SEND_TO_LISTENER(LISTENER_TYPE, TYPE_NAME, FD, STRING)                        \
      client_t* client;                                                               \
      int listener_cnt = 0;                                                           \
      for(client = client_lst; client; client = client->next)                         \
        if(client->LISTENER_TYPE && client->fd != FD) {                               \
          send_response(client->fd, STRING);                                          \
          listener_cnt++;                                                             \
        }                                                                             \
      log_printf(DEBUG, "sent %s to %d additional listeners", TYPE_NAME,listener_cnt);
  

int process_cmd(char* cmd, int fd, cmd_t **cmd_q, client_t* client_lst, options_t* opt)
{
  log_printf(DEBUG, "processing command from %d", fd);

  if(!cmd_q || !cmd)
    return -1;
  
  cmd_id_t cmd_id;
  if(!strncmp(cmd, "power on", 8)) {
    cmd_id = POWER_ON;
    cmd[5] = '_';
  }
  else if(!strncmp(cmd, "power off", 9)) {
    cmd_id = POWER_OFF;
    cmd[5] = '_';
  }
  else if(!strncmp(cmd, "sample", 6))
    cmd_id = SAMPLE;
  else if(!strncmp(cmd, "log", 3))
    cmd_id = LOG;
  else if(!strncmp(cmd, "listen", 6)) {
    cmd_id = LISTEN;
  }
  else {
    log_printf(WARNING, "unknown command '%s'", cmd);
    return 0;
  }
  char* param = strchr(cmd, ' ');
  if(param)
    param++;

  if(cmd_id == POWER_ON || cmd_id == POWER_OFF) {
    char* orig_param = param;
    param = key_value_storage_find(&opt->powerids_, param);
    if(!param) {
      send_response(fd, "Error: invalid power id");
      log_printf(WARNING, "invalid power id '%s' in command from %d", orig_param, fd);
    }
  }

  if(cmd_id == SAMPLE) {
    char* orig_param = param;
    param = key_value_storage_find(&opt->sampledevs_, param);
    if(!param) {
      send_response(fd, "Error: invalid sample device");
      log_printf(WARNING, "invalid sample device '%s' in command from %d", orig_param, fd);
    }
  }

  if(cmd_id == POWER_ON || cmd_id == POWER_OFF || cmd_id == SAMPLE) {
    char* resp;
    asprintf(&resp, "Request: %s", cmd);
    if(resp) {
      char* linefeed = strchr(resp, '\n');
      if(linefeed) linefeed[0] = 0;
      SEND_TO_LISTENER(request_listener, "request", fd, resp);
      free(resp);
    }
// else silently ignore memory alloc error
  }

  switch(cmd_id) {
  case POWER_ON:
  case POWER_OFF:
  case SAMPLE: {
    int ret = cmd_push(cmd_q, fd, cmd_id, param);
    if(ret)
      return ret;

    log_printf(NOTICE, "command: %s", cmd); 
    break;
  }
  case LOG: {
    if(param && param[0])
      log_printf(NOTICE, "ext msg: %s", param); 
    else
      log_printf(DEBUG, "ignoring empty ext log message");
    break;
  }
  case LISTEN: {
    client_t* listener = client_find(client_lst, fd);
    if(listener) {
      if(!param || !strncmp(param, "all", 3)) {
        listener->request_listener = 1;
        listener->error_listener = 1;
        listener->temp_listener = 1;
        listener->photo_listener = 1;
        listener->movement_listener = 1;
        listener->button_listener = 1;
      }
      else if(!strncmp(param, "none", 4)) {
        listener->request_listener = 0;
        listener->error_listener = 0;
        listener->temp_listener = 0;
        listener->photo_listener = 0;
        listener->movement_listener = 0;
        listener->button_listener = 0;
      }
      else if(!strncmp(param, "request", 7))
        listener->request_listener = 1;
      else if(!strncmp(param, "error", 5))
        listener->error_listener = 1;
      else if(!strncmp(param, "temp", 4))
        listener->temp_listener = 1;      
      else if(!strncmp(param, "photo", 5))
        listener->photo_listener = 1;      
      else if(!strncmp(param, "movement", 8))
        listener->movement_listener = 1;      
      else if(!strncmp(param, "button", 6))
        listener->button_listener = 1;      
      else {
        log_printf(DEBUG, "unkown listener type '%s'", param);
        break;
      }
      log_printf(DEBUG, "listener %d requests %s messages", fd, param ? param:"all");
    }
    else {
      log_printf(ERROR, "unable to add listener %d", fd);
    }
    break;
  }
  }
  
  return 0;
}

int nonblock_readline(read_buffer_t* buffer, int fd, cmd_t** cmd_q, client_t* client_lst, options_t* opt)
{
  int ret = 0;
  for(;;) {
    ret = read(fd, &buffer->buf[buffer->offset], 1);
    if(!ret || (ret == -1 && errno == EBADF))
      return 2;
    if(ret == -1 && (errno == EAGAIN || errno == EWOULDBLOCK))
      return 0;
    else if(ret < 0)
      break;

    if(buffer->buf[buffer->offset] == '\n') {
      buffer->buf[buffer->offset] = 0;
      ret = process_cmd(buffer->buf, fd, cmd_q, client_lst, opt);
      buffer->offset = 0;
      break;
    }

    buffer->offset++;
    if(buffer->offset >= sizeof(buffer->buf)) {
      log_printf(DEBUG, "string too long (fd=%d)", fd);
      buffer->offset = 0;
      return 0;
    }
  }

  return ret;
}

int process_tty(read_buffer_t* buffer, int tty_fd, cmd_t **cmd_q, client_t* client_lst)
{
  int ret = 0;
  struct timeval tv;
  fd_set fds;
  FD_ZERO(&fds);
  FD_SET(tty_fd, &fds);

  for(;;) {
    tv.tv_sec = 0;
    tv.tv_usec = 0;
    ret = select(tty_fd+1, &fds, NULL, NULL, &tv);
    if(!ret)
      return 0;
    else if(ret < 0)
      return ret;

    ret = read(tty_fd, &buffer->buf[buffer->offset], 1);
    if(!ret)
      return 2;
    if(ret == -1 && errno == EAGAIN)
      return 0;
    else if(ret < 0)
      break;

    if(buffer->buf[buffer->offset] == '\n') {
      buffer->buf[buffer->offset] = 0;

      if(buffer->offset > 0 && buffer->buf[buffer->offset-1] == '\r')
        buffer->buf[buffer->offset-1] = 0;

      log_printf(NOTICE, "firmware: %s", buffer->buf);      

      int cmd_fd = -1;
      if(cmd_q && (*cmd_q)) {
        cmd_fd = (*cmd_q)->fd;
        send_response(cmd_fd, buffer->buf);
      }
      
      if(!strncmp(buffer->buf, "Error:", 6)) {
        SEND_TO_LISTENER(error_listener, "error", cmd_fd, buffer->buf);
      }
      
      if(!strncmp(buffer->buf, "movement", 8)) {
        SEND_TO_LISTENER(movement_listener, "movement", cmd_fd, buffer->buf);
      }

      if(!strncmp(buffer->buf, "PanicButton", 11)) {
        SEND_TO_LISTENER(button_listener, "panic buttont", cmd_fd, buffer->buf);
      }

      if(!strncmp(buffer->buf, "Temp ", 5)) {
        SEND_TO_LISTENER(temp_listener, "", cmd_fd, buffer->buf);
      }

      cmd_pop(cmd_q);
      buffer->offset = 0;
      return 0;
    }

    buffer->offset++;
    if(buffer->offset >= sizeof(buffer->buf)) {
      log_printf(DEBUG, "string too long (fd=%d)", tty_fd);
      buffer->offset = 0;
      return 0;
    }
  }

  return ret;
}

int main_loop(int tty_fd, int cmd_listen_fd, int autosample_fd, options_t* opt)
{
  log_printf(NOTICE, "entering main loop");

  clear_fd(tty_fd);
  clear_fd(autosample_fd);

  fd_set readfds, tmpfds;
  FD_ZERO(&readfds);
  FD_SET(tty_fd, &readfds);
  FD_SET(cmd_listen_fd, &readfds);
  int max_fd = tty_fd > cmd_listen_fd ? tty_fd : cmd_listen_fd;
  FD_SET(autosample_fd, &readfds);
  max_fd = (max_fd < autosample_fd) ? autosample_fd : max_fd;
  cmd_t* cmd_q = NULL;
  client_t* client_lst = NULL;

  read_buffer_t tty_buffer;
  tty_buffer.offset = 0;
  read_buffer_t autosample_buffer;
  autosample_buffer.offset = 0;

  int sig_fd = signal_init();
  if(sig_fd < 0)
    return -1;
  FD_SET(sig_fd, &readfds);
  max_fd = (max_fd < sig_fd) ? sig_fd : max_fd;

  struct timeval timeout;
  int return_value = 0;
  while(!return_value) {
    memcpy(&tmpfds, &readfds, sizeof(tmpfds));

    timeout.tv_sec = 0;
    timeout.tv_usec = 200000;
    int ret = select(max_fd+1, &tmpfds, NULL, NULL, &timeout);
    if(ret == -1 && errno != EINTR) {
      log_printf(ERROR, "select returned with error: %s", strerror(errno));
      return_value = -1;
      break;
    }
    if(ret == -1)
      continue;
    if(!ret) {
      if(cmd_q && cmd_has_expired(*cmd_q)) {
        log_printf(ERROR, "last command expired");
        cmd_pop(&cmd_q);
      }
      else
        continue;
    }

    if(FD_ISSET(sig_fd, &tmpfds)) {
      if(signal_handle()) {
        return_value = 1;
        break;
      }
    }
   
    if(FD_ISSET(tty_fd, &tmpfds)) {
      return_value = process_tty(&tty_buffer, tty_fd, &cmd_q, client_lst);
      if(return_value)
        break;
    }

    if(FD_ISSET(cmd_listen_fd, &tmpfds)) {
      int new_fd = accept(cmd_listen_fd, NULL, NULL);
      if(new_fd < 0) {
        log_printf(ERROR, "accept returned with error: %s", strerror(errno));
        return_value = -1;
        break;
      }  
      log_printf(DEBUG, "new command connection (fd=%d)", new_fd);
      FD_SET(new_fd, &readfds);
      max_fd = (max_fd < new_fd) ? new_fd : max_fd;
      fcntl(new_fd, F_SETFL, O_NONBLOCK);
      client_add(&client_lst, new_fd);
    }

    if(FD_ISSET(autosample_fd, &tmpfds)) {
      return_value = nonblock_readline(&autosample_buffer, autosample_fd, &cmd_q, client_lst, opt);
      if(return_value == 2) {
        log_printf(WARNING, "autosample not running, removing pipe to it");
        FD_CLR(autosample_fd, &readfds);
        return_value = 0;
        continue;
      }
      if(return_value)
        break;
    }

    client_t* lst = client_lst;
    while(lst) {
      if(FD_ISSET(lst->fd, &tmpfds)) {
        return_value = nonblock_readline(&(lst->buffer), lst->fd, &cmd_q, client_lst, opt);
        if(return_value == 2) {
          log_printf(DEBUG, "removing closed command connection (fd=%d)", lst->fd);
          client_t* deletee = lst;
          lst = lst->next;
          FD_CLR(deletee->fd, &readfds);
          client_remove(&client_lst, deletee->fd);
          return_value = 0;
          continue;
        }
        if(return_value)
          break;

      }
      lst = lst->next;
    }

    if(cmd_q && !cmd_q->sent)
      send_command(tty_fd, cmd_q);
  }

  cmd_clear(&cmd_q);
  client_clear(&client_lst);
  signal_stop();
  return return_value;
}

int setup_tty(int fd)
{
  struct termios tmio;
  
  int ret = tcgetattr(fd, &tmio);
  if(ret) {
    log_printf(ERROR, "Error on tcgetattr(): %s", strerror(errno));
    return ret;
  }

  ret = cfsetospeed(&tmio, B9600);
  if(ret) {
    log_printf(ERROR, "Error on cfsetospeed(): %s", strerror(errno));
    return ret;
  }

  ret = cfsetispeed(&tmio, B9600);
  if(ret) {
    log_printf(ERROR, "Error on cfsetispeed(): %s", strerror(errno));
    return ret;
  }

  tmio.c_lflag &= ~ECHO;

  ret = tcsetattr(fd, TCSANOW, &tmio);
  if(ret) {
    log_printf(ERROR, "Error on tcsetattr(): %s", strerror(errno));
    return ret;
  }
  
  ret = tcflush(fd, TCIFLUSH);
  if(ret) {
    log_printf(ERROR, "Error on tcflush(): %s", strerror(errno));
    return ret;
  }

  clear_fd(fd);

  return 0;
}

int main(int argc, char* argv[])
{
  log_init();

  options_t opt;
  int ret = options_parse(&opt, argc, argv);
  if(ret) {
    if(ret > 0) {
      fprintf(stderr, "syntax error near: %s\n\n", argv[ret]);
    }
    if(ret == -2) {
      fprintf(stderr, "memory error on options_parse, exiting\n");
    }

    if(ret != -2)
      options_print_usage();

    options_clear(&opt);
    log_close();
    exit(ret);
  }
  string_list_element_t* tmp = opt.log_targets_.first_;
  if(!tmp) {
    log_add_target("syslog:3,powersensordaemon,daemon");
  }
  else {
    while(tmp) {
      ret = log_add_target(tmp->string_);
      if(ret) {
        switch(ret) {
        case -2: fprintf(stderr, "memory error on log_add_target, exitting\n"); break;
        case -3: fprintf(stderr, "unknown log target: '%s', exitting\n", tmp->string_); break;
        case -4: fprintf(stderr, "this log target is only allowed once: '%s', exitting\n", tmp->string_); break;
        default: fprintf(stderr, "syntax error near: '%s', exitting\n", tmp->string_); break;
        }
        
        options_clear(&opt);
        log_close();
        exit(ret);
      }
      tmp = tmp->next_;
    }
  }
  log_printf(NOTICE, "just started...");
  if(options_parse_post(&opt)) {
    options_clear(&opt);
    log_close();
    exit(-1);
  }

  priv_info_t priv;
  if(opt.username_)
    if(priv_init(&priv, opt.username_, opt.groupname_)) {
      options_clear(&opt);
      log_close();
      exit(-1);
    }

  FILE* pid_file = NULL;
  if(opt.pid_file_) {
    pid_file = fopen(opt.pid_file_, "w");
    if(!pid_file) {
      log_printf(WARNING, "unable to open pid file: %s", strerror(errno));
    }
  }

  if(opt.chroot_dir_)
    if(do_chroot(opt.chroot_dir_)) {
      options_clear(&opt);
      log_close();
      exit(-1);
    }
  if(opt.username_)
    if(priv_drop(&priv)) {
      options_clear(&opt);
      log_close();
      exit(-1);
    }

  if(opt.daemonize_) {
    pid_t oldpid = getpid();
    daemonize();
    log_printf(INFO, "running in background now (old pid: %d)", oldpid);
  }

  if(pid_file) {
    pid_t pid = getpid();
    fprintf(pid_file, "%d", pid);
    fclose(pid_file);
  }
  
  int autosample_fd = -1;
  if(key_value_storage_length(&opt.autosampledevs_) > 0) {
    log_printf(NOTICE, "starting autosample process");
    autosample_fd = start_autosample_process(&opt);
    if(autosample_fd == -1) {
      options_clear(&opt);
      log_close();
      exit(1);
    }
    else if(autosample_fd <= 0) {
      if(!autosample_fd)
        log_printf(NOTICE, "autosample process normal shutdown");
      else if(autosample_fd == -2)
        log_printf(NOTICE, "autosample shutdown after signal");
      else
        log_printf(NOTICE, "autosample shutdown after error");
      
      options_clear(&opt);
      log_close();
      exit(1);
    }
  }

  int cmd_listen_fd = init_command_socket(opt.command_sock_);
  if(cmd_listen_fd < 0) {
    options_clear(&opt);
    log_close();
    exit(-1);
  }
  
  int tty_fd = 0;
  for(;;) {
    tty_fd = open(opt.tty_dev_, O_RDWR | O_NOCTTY);
    if(tty_fd < 0)
      ret = 2;
    else {
      ret = setup_tty(tty_fd);
      if(ret)
        ret = 2;
      else
        ret = main_loop(tty_fd, cmd_listen_fd, autosample_fd, &opt);
    }

    if(ret == 2) {
      log_printf(ERROR, "%s error, trying to reopen in 5 seconds..", opt.tty_dev_);
      if(tty_fd > 0)
        close(tty_fd);
      sleep(5);
    }
    else
      break;
  }

  close(cmd_listen_fd);
  if(tty_fd > 0)
    close(tty_fd);

  if(!ret)
    log_printf(NOTICE, "normal shutdown");
  else if(ret < 0)
    log_printf(NOTICE, "shutdown after error");
  else
    log_printf(NOTICE, "shutdown after signal");

  options_clear(&opt);
  log_close();

  return ret;
}
