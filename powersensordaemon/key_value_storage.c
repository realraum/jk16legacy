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

#include <stdio.h>
#include <string.h>

#include "key_value_storage.h"

void key_value_storage_init(key_value_storage_t* stor)
{
  if(!stor)
    return;

  string_list_init(&(stor->keys_));
  string_list_init(&(stor->values_));
}

void key_value_storage_clear(key_value_storage_t* stor)
{
  if(!stor)
    return;

  string_list_clear(&(stor->keys_));
  string_list_clear(&(stor->values_));
}

int key_value_storage_add(key_value_storage_t* stor, const char* key, const char* value)
{
  if(!stor || !key || !value)
    return -1;

  int ret = string_list_add(&(stor->keys_), key);
  if(ret!=0) 
    return ret;

  ret = string_list_add(&(stor->values_), value);
  if(ret!=0) 
    return ret;

  return 0;
}

char* key_value_storage_find(key_value_storage_t* stor, const char* key)
{
  if(!stor || !key)
    return NULL;

  string_list_element_t* k = stor->keys_.first_;
  string_list_element_t* v = stor->values_.first_;
  while(v && k) {
    if(!strcmp(k->string_, key))
      return v->string_;
    
    k = k->next_;
    v = v->next_;
  }

  return NULL;
}

/* Warning: this function only works if you actually store \0-terminated strings as values!! */
char const * key_value_storage_find_first_stringvalue(key_value_storage_t* stor, char const * value)
{
  if(!stor || !value)
    return NULL;

  string_list_element_t* k = stor->keys_.first_;
  string_list_element_t* v = stor->values_.first_;
  while(v && k) {
    if(!strcmp(v->string_, value))
      return k->string_;
    
    k = k->next_;
    v = v->next_;
  }

  return NULL;
}

int key_value_storage_length(key_value_storage_t* stor)
{
  if(!stor)
    return 0;

  int length = 0;
  string_list_element_t* k = stor->keys_.first_;
  while(k) {
    length++;
    k = k->next_;
  }

  return length;
}

void key_value_storage_print(key_value_storage_t* stor, const char* head, const char* sep, const char* tail)
{
  if(!stor)
    return;

  string_list_element_t* k = stor->keys_.first_;
  string_list_element_t* v = stor->values_.first_;
  while(v && k) {
    printf("%s%s%s%s%s", head, k->string_, sep, v->string_, tail);
    k = k->next_;
    v = v->next_;
  }
  printf("\n");
}
