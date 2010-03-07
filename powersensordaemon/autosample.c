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

#include <unistd.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <errno.h>

#include "autosample.h"
 
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
          // timout has expired...
      write(pipefd, "sample temp0", 12);
      char c = '\n';
      write(pipefd, &c, 1);
    }

    if(FD_ISSET(sig_fd, &readfds)) {
      if(signal_handle()) {
        return_value = -2;
        break;
      }
    } 
  }

  signal_stop();
  return return_value;
}





