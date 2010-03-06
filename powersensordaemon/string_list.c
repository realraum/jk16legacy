/*
 *  uAnytun
 *
 *  uAnytun is a tiny implementation of SATP. Unlike Anytun which is a full
 *  featured implementation uAnytun has no support for multiple connections
 *  or synchronisation. It is a small single threaded implementation intended
 *  to act as a client on small platforms.
 *  The secure anycast tunneling protocol (satp) defines a protocol used
 *  for communication between any combination of unicast and anycast
 *  tunnel endpoints.  It has less protocol overhead than IPSec in Tunnel
 *  mode and allows tunneling of every ETHER TYPE protocol (e.g.
 *  ethernet, ip, arp ...). satp directly includes cryptography and
 *  message authentication based on the methodes used by SRTP.  It is
 *  intended to deliver a generic, scaleable and secure solution for
 *  tunneling and relaying of packets of any protocol.
 *  
 *
 *  Copyright (C) 2007-2008 Christian Pointner <equinox@anytun.org>
 *
 *  This file is part of uAnytun.
 *
 *  uAnytun is free software: you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation, either version 3 of the License, or
 *  any later version.
 *
 *  uAnytun is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with uAnytun. If not, see <http://www.gnu.org/licenses/>.
 */

#include <string.h>
#include <stdlib.h>
#include <stdio.h>

#include "string_list.h"

void string_list_init(string_list_t* list)
{
  if(!list)
    return;
  
  list->first_ = NULL;
}

void string_list_clear(string_list_t* list)
{
  if(!list)
    return;

  while(list->first_) {
    string_list_element_t* tmp;
    tmp = list->first_;
    list->first_ = tmp->next_;
    if(tmp->string_)
      free(tmp->string_);
    free(tmp);
  }
}

int string_list_add(string_list_t* list, const char* string)
{
  if(!list)
    return -1;

  if(!list->first_) {
    list->first_ = malloc(sizeof(string_list_element_t));
    if(!list->first_)
      return -2;

    list->first_->next_ = 0;
    list->first_->string_ = strdup(string);
    if(!list->first_->string_) {
      free(list->first_);
      list->first_ = NULL;
      return -2;
    }
  }
  else {
    string_list_element_t* tmp = list->first_;
    while(tmp->next_)
      tmp = tmp->next_;

    tmp->next_  = malloc(sizeof(string_list_element_t));
    if(!tmp->next_)
      return -2;

    tmp->next_->next_ = 0;
    tmp->next_->string_ = strdup(string);
    if(!tmp->next_->string_) {
      free(tmp->next_);
      tmp->next_ = NULL;
      return -2;
    }
  }
  return 0;
}

void string_list_print(string_list_t* list, const char* head, const char* tail)
{
  if(!list)
    return;
  
  string_list_element_t* tmp = list->first_;
  while(tmp) {
    printf("%s%s%s", head, tmp->string_, tail);
    tmp = tmp->next_;
  }
}
