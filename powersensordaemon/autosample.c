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
#include <string.h>
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

int start_autosample_process(options_t* opt, autosample_process_t* a)
{
  int write_pipefd[2];
  int read_pipefd[2];
  pid_t cpid;
  
  if (pipe(write_pipefd) == -1) {
    log_printf(ERROR, "autosample_process: pipe() failed: %s", strerror(errno));
    return -1;
  }

  if (pipe(read_pipefd) == -1) {
    log_printf(ERROR, "autosample_process: pipe() failed: %s", strerror(errno));
    close(write_pipefd[0]);
    close(write_pipefd[1]);
    return -1;
  }
  
  cpid = fork();
  if (cpid == -1) {
    log_printf(ERROR, "autosample_process: fork() failed: %s", strerror(errno));
    close(write_pipefd[0]);
    close(write_pipefd[1]);
    close(read_pipefd[0]);
    close(read_pipefd[1]);
    return -1;
  }
  
  if (cpid == 0) {
    close(write_pipefd[0]);
    close(read_pipefd[1]);
    int ret = autosample_process(opt, write_pipefd[1], read_pipefd[0]);
    if(!ret)
      log_printf(NOTICE, "autosample process normal shutdown");
    else if(ret > 0)
      log_printf(NOTICE, "autosample shutdown after signal");
    else
      log_printf(NOTICE, "autosample shutdown after error");
    
    options_clear(opt);
    log_close();
    exit(0);
  }

  close(write_pipefd[1]);
  close(read_pipefd[0]);
  a->pid_ = cpid;
  a->write_fd_ = write_pipefd[0];
  a->read_fd_ = read_pipefd[1];
  return 0;
}

int autosample_process(options_t *opt, int writefd, int readfd)
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
    return -1;

  fd_set readfds, tmpfds;
  FD_ZERO(&readfds);
  FD_SET(readfd, &readfds);
  FD_SET(sig_fd, &readfds);
  int max_fd = (readfd < sig_fd) ? sig_fd : readfd;

  struct timeval timeout;
  int return_value = 0;
  unsigned char sample_enabled = 0;
  while(!return_value) {
    memcpy(&tmpfds, &readfds, sizeof(tmpfds));
    timeout.tv_sec = 0;
    timeout.tv_usec = 1000000;
    int ret = select(max_fd+1, &tmpfds, NULL, NULL, &timeout);
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
          if(sample_enabled) {
            log_printf(DEBUG, "autosample send sample command for '%s'", devices[i].device_name_);
            send_sample_cmd(writefd, devices[i].device_name_);
          }
          devices[i].cnt_ = 0;
        }
      }
    }

    if(FD_ISSET(readfd, &tmpfds)) {
      int ret;
      do {
        ret = read(readfd, &sample_enabled, 1);
      } while(!ret || (ret == -1 && errno == EINTR));
      log_printf(NOTICE, "autosample %s", sample_enabled == 0 ? "disabled" : "enabled");
    }

    if(FD_ISSET(sig_fd, &tmpfds)) {
      if(signal_handle()) {
        return_value = 1;
        break;
      }
    } 
  }

  signal_stop();
  free(devices);
  return return_value;
}





