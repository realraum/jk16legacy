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

#ifndef POWERSENSORDAEMON_autosample_h_INCLUDED
#define POWERSENSORDAEMON_autosample_h_INCLUDED

#include "options.h"

struct autosample_process_struct {
  pid_t pid_;
  int read_fd_;
  int write_fd_;
};
typedef struct autosample_process_struct autosample_process_t;

struct autosample_device_struct {
  int delay_;
  int cnt_;
  char* device_name_;
};
typedef struct autosample_device_struct autosample_device_t;

int send_sample_cmd(int fd, const char* device_name);
int start_autosample_process(options_t* opt, autosample_process_t* a);
int autosample_process(options_t *opt, int writefd, int readfd);

#endif
