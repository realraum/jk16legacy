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

#ifndef POWERSENSORDAEMON_client_list_h_INCLUDED
#define POWERSENSORDAEMON_client_list_h_INCLUDED

#include "datatypes.h"

struct client_struct {
  int fd;
  int request_listener;
  int error_listener;
  int temp_listener;
  int photo_listener;
  int movement_listener;
  int button_listener;
  struct client_struct* next;
  read_buffer_t buffer;
};
typedef struct client_struct client_t;

int client_add(client_t** first, int fd);
void client_remove(client_t** first, int fd);
client_t* client_find(client_t* first, int fd);
void client_clear(client_t** first);

#endif
