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

#include "options.h"
#include "log.h"

#include <stdlib.h>
#include <stdio.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <errno.h>

#include "autosample.h"
 
int send_sample_cmd(int fd, const char* device_name)
{
  if(!device_name)
    return -1;

  char* buf;
  int len = asprintf(&buf, "sample %s\n", device_name);
  if(len <= 0)
    return len;
  int offset = 0;
  int ret;
  for(;;) {
    ret = write(fd, &buf[offset], len - offset);
    if(ret < 0) {
      if(errno != EINTR) {
        free(buf);
        return ret;
      }

      ret = 0;
    }

    offset += ret;
    if(offset+1 >= len)
      break;
  }
  free(buf);

  if(ret > 0)
    return 0;

  return ret;
}

int start_autosample_process(options_t* opt)
{
  int pipefd[2];
  pid_t cpid;
  
  if (pipe(pipefd) == -1) {
    log_printf(ERROR, "autosample_process: pipe() failed: %s", strerror(errno));
    return -1;
  }
  
  cpid = fork();
  if (cpid == -1) {
    log_printf(ERROR, "autosample_process: fork() failed: %s", strerror(errno));
    close(pipefd[0]);
    close(pipefd[1]);
    return -1;
  }
  
  if (cpid == 0) {
    close(pipefd[0]);
    return autosample_process(opt, pipefd[1]);
  }

  close(pipefd[1]);
  return pipefd[0];
}

int autosample_process(options_t *opt, int pipefd)
{
  log_printf(NOTICE, "autosample process just started");

  int device_num = key_value_storage_length(&opt->autosampledevs_);
  if(device_num <= 0) {
    log_printf(WARNING, "autosample no devices to sample, exiting");
    return 0;
  }

  autosample_device_t* devices = malloc(sizeof(autosample_device_t)*device_num);
  if(!devices) {
    log_printf(WARNING, "autosample memory error, exiting");
    return -3;
  }

  int i = 0;
  string_list_element_t* k = opt->autosampledevs_.keys_.first_;
  string_list_element_t* v = opt->autosampledevs_.values_.first_;
  while(k && v) {
    devices[i].delay_ = atoi(v->string_);
    devices[i].cnt_ = 0;
    devices[i].device_name_ = k->string_;
    k = k->next_;
    v = v->next_;
  }

  int sig_fd = signal_init();
  if(sig_fd < 0)
    return -3;

  fd_set readfds;
  struct timeval timeout;
  int return_value = 0;
  while(!return_value) {
    FD_SET(sig_fd, &readfds);
    timeout.tv_sec = 0;
    timeout.tv_usec = 1000000;
    int ret = select(sig_fd+1, &readfds, NULL, NULL, &timeout);
    if(ret == -1 && errno != EINTR) {
      log_printf(ERROR, "autosample process select returned with error: %s", strerror(errno));
      return_value = -3;
      break;
    }
    if(ret == -1)
      continue;
    if(!ret) {
      int i;
      for(i = 0; i < device_num; i++) {
        devices[i].cnt_++;
        if(devices[i].cnt_ >= devices[i].delay_) {
          log_printf(DEBUG, "autosample send sample command for '%s'", devices[i].device_name_);
          send_sample_cmd(pipefd, devices[i].device_name_);
          devices[i].cnt_ = 0;
        }
      }
    }

    if(FD_ISSET(sig_fd, &readfds)) {
      if(signal_handle()) {
        return_value = -2;
        break;
      }
    } 
  }

  signal_stop();
  free(devices);
  return return_value;
}





