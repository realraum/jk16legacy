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

#ifndef POWERSENSORDAEMON_options_h_INCLUDED
#define POWERSENSORDAEMON_options_h_INCLUDED

#include "string_list.h"
#include "key_value_storage.h"

struct options_struct {
  char* progname_;
  int daemonize_;
  char* username_;
  char* groupname_;
  char* chroot_dir_;
  char* pid_file_;
  string_list_t log_targets_;

  char* tty_dev_;
  char* command_sock_;
  char* powerid_file_;
  key_value_storage_t powerids_;
  char* sampledev_file_;
  key_value_storage_t sampledevs_;
};
typedef struct options_struct options_t;

int options_parse_hex_string(const char* hex, buffer_t* buffer);

int options_parse(options_t* opt, int argc, char* argv[]);
int options_parse_key_value_file(const char* filename, key_value_storage_t* storage);
int options_parse_post(options_t* opt);
void options_default(options_t* opt);
void options_clear(options_t* opt);
void options_print_usage();
void options_print(options_t* opt);

#endif
