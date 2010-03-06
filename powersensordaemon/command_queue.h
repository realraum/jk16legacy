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

#ifndef POWERSENSORDAEMON_command_queue_h_INCLUDED
#define POWERSENSORDAEMON_command_queue_h_INCLUDED

#include <sys/time.h>

enum cmd_id_enum { POWER_ON, POWER_OFF, SAMPLE, LOG , LISTEN };
typedef enum cmd_id_enum cmd_id_t;

struct cmd_struct {
  int fd;
  cmd_id_t cmd;
  char* param;
  int sent;
  struct timeval tv_start;
  struct cmd_struct* next;
};
typedef struct cmd_struct cmd_t;

int cmd_push(cmd_t** first, int fd, cmd_id_t cmd, const char* param);
void cmd_sent(cmd_t* cmd);
int cmd_has_expired(cmd_t cmd);
void cmd_pop(cmd_t** first);
void cmd_clear(cmd_t** first);

#endif
