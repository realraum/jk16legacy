/*
 *  rhctl
 *
 *  Copyright (C) 2009 Christian Pointner <equinox@spreadspace.org>
 *
 *  This file is part of rhctl.
 *
 *  rhctl is free software: you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation, either version 3 of the License, or
 *  any later version.
 *
 *  rhctl is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with rhctl. If not, see <http://www.gnu.org/licenses/>.
 */

#ifndef RHCTL_key_value_storage_h_INCLUDED
#define RHCTL_key_value_storage_h_INCLUDED

#include "string_list.h"

struct key_value_storage_struct {
  string_list_t keys_;
  string_list_t values_;
};
typedef struct key_value_storage_struct key_value_storage_t;

void key_value_storage_init(key_value_storage_t* stor);
void key_value_storage_clear(key_value_storage_t* stor);
int key_value_storage_add(key_value_storage_t* stor, const char* key, const char* value);
char* key_value_storage_find(key_value_storage_t* stor, const char* key);
int key_value_storage_length(key_value_storage_t* stor);

void key_value_storage_print(key_value_storage_t* stor, const char* head, const char* sep, const char* tail);


#endif
