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

#include <stdlib.h>
#include <string.h>

#include "command_queue.h"
#include "datatypes.h"

cmd_t* cmd_get_last(cmd_t* first)
{
  if(!first) 
    return NULL;

  while(first->next) {
    first = first->next;
  }

  return first;
}

int cmd_push(cmd_t** first, int fd, cmd_id_t cmd, const char* param)
{
  if(!first)
    return -1;

  cmd_t* new_cmd = malloc(sizeof(cmd_t));
  if(!new_cmd)
    return -2;

  new_cmd->fd = fd;
  new_cmd->cmd = cmd;
  if(param) {
    new_cmd->param = strdup(param);
    if(!new_cmd->param) {
      free(new_cmd);
      return -2;
    }
  }
  else
    new_cmd->param = NULL;
  new_cmd->sent = 0;
  new_cmd->tv_start.tv_sec = 0;
  new_cmd->tv_start.tv_usec = 0;
  new_cmd->next = NULL;

  if(!(*first)) {
    *first = new_cmd;
    return 0;
  }
    
  cmd_get_last(*first)->next = new_cmd;

  return 0;
}

void cmd_sent(cmd_t* cmd)
{
  if(!cmd)
    return;

  cmd->sent = 1;
  gettimeofday(&cmd->tv_start, NULL);
}

int cmd_has_expired(cmd_t cmd)
{
  struct timeval now;
  timerclear(&now);
  gettimeofday(&now, NULL);
  cmd.tv_start.tv_sec+=2;

  return timercmp(&cmd.tv_start, &now, <);
}

void cmd_pop(cmd_t** first)
{
  if(!first || !(*first)) 
    return;

  cmd_t* deletee = *first;
  *first = (*first)->next;
  if(deletee->param)
    free(deletee->param);
  free(deletee);
}

void cmd_clear(cmd_t** first)
{
  if(!first || !(*first)) 
    return;

  while(*first) {
    cmd_t* deletee = *first;
    *first = (*first)->next;
    if(deletee->param)
      free(deletee->param);
    free(deletee);
  }
}
