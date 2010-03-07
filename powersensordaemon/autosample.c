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
    close(pipefd[1]);
    return autosample_process(opt, pipefd[0]);
  }

  close(pipefd[0]);
  return pipefd[1];
}

int autosample_process(options_t *opt, int pipefd)
{
  log_printf(NOTICE, "autosample process just started");

  sleep(5);

  return 0;
}





