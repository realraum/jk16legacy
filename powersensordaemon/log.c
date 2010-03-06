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

#include "datatypes.h"

#include <string.h>
#include <stdarg.h>
#include <stdlib.h>
#include <stdio.h>

#define SYSLOG_NAMES
#include <syslog.h>

#include "log.h"

log_t stdlog;

#include "log_targets.h"

const char* log_prio_to_string(log_prio_t prio)
{
  switch(prio) {
  case ERROR: return "ERROR";
  case WARNING: return "WARNING";
  case NOTICE: return "NOTICE";
  case INFO: return "INFO";
  case DEBUG: return "DEBUG";
  }
  return "UNKNOWN";
}

log_target_type_t log_target_parse_type(const char* conf)
{
  if(!conf)
    return TARGET_UNKNOWN;

  if(!strncmp(conf, "syslog", 6)) return TARGET_SYSLOG;
  if(!strncmp(conf, "file", 4)) return TARGET_FILE;
  if(!strncmp(conf, "stdout", 6)) return TARGET_STDOUT;
  if(!strncmp(conf, "stderr", 6)) return TARGET_STDERR;

  return TARGET_UNKNOWN;
}

int log_targets_target_exists(log_targets_t* targets, log_target_type_t type)
{
  if(!targets && !targets->first_)
    return 0;

  log_target_t* tmp = targets->first_;
  while(tmp) {
    if(tmp->type_ == type)
      return 1;
    tmp = tmp->next_;
  }  
  return 0;
}

int log_targets_add(log_targets_t* targets, const char* conf)
{
  if(!targets)
    return -1;

  log_target_t* new_target = NULL;
  int duplicates_allowed = 0;
  switch(log_target_parse_type(conf)) {
  case TARGET_SYSLOG: new_target = log_target_syslog_new(); break;
  case TARGET_FILE: new_target = log_target_file_new(); duplicates_allowed = 1; break;
  case TARGET_STDOUT: new_target = log_target_stdout_new(); break;
  case TARGET_STDERR: new_target = log_target_stderr_new(); break;
  default: return -3;
  }
  if(!new_target)
    return -2;

  if(!duplicates_allowed && log_targets_target_exists(targets, new_target->type_)) {
    free(new_target);
    return -4;
  }

  const char* prioptr = strchr(conf, ':');
  if(!prioptr || prioptr[1] == 0) {
    free(new_target);
    return -1;
  }
  prioptr++;
  if(!isdigit(prioptr[0]) || (prioptr[1] != 0 && prioptr[1] != ',')) {
    free(new_target);
    return -1;
  }
  new_target->max_prio_ = prioptr[0] - '0';
  if(new_target->max_prio_ > 0)
    new_target->enabled_ = 1;

  if(new_target->init != NULL) {
    const char* confptr = NULL;
    if(prioptr[1] != 0)
      confptr = prioptr+2;

    int ret = (*new_target->init)(new_target, confptr);
    if(ret) {
      free(new_target);
      return ret;
    }
  }

  if(new_target->open != NULL)
    (*new_target->open)(new_target);


  if(!targets->first_) {
    targets->first_ = new_target;
  }
  else {
    log_target_t* tmp = targets->first_;
    while(tmp->next_)
      tmp = tmp->next_;
    
    tmp->next_ = new_target;
  }
  return 0;
}

void log_targets_log(log_targets_t* targets, log_prio_t prio, const char* msg)
{
  if(!targets)
    return;

  log_target_t* tmp = targets->first_;
  while(tmp) {
    if(tmp->log != NULL && tmp->enabled_ && tmp->max_prio_ >= prio)
      (*tmp->log)(tmp, prio, msg);

    tmp = tmp->next_;
  }
}

void log_targets_clear(log_targets_t* targets)
{
  if(!targets)
    return;

  while(targets->first_) {
    log_target_t* tmp = targets->first_;
    targets->first_ = tmp->next_;
    if(tmp->close != NULL)
      (*tmp->close)(tmp);
    if(tmp->clear != NULL)
      (*tmp->clear)(tmp);
    free(tmp);
  }
}


void log_init()
{
  stdlog.max_prio_ = 0;
  stdlog.targets_.first_ = NULL;
}

void log_close()
{
  log_targets_clear(&stdlog.targets_);
}

void update_max_prio()
{
  log_target_t* tmp = stdlog.targets_.first_;
  while(tmp) {
    if(tmp->enabled_ && tmp->max_prio_ > stdlog.max_prio_)
      stdlog.max_prio_ = tmp->max_prio_;

    tmp = tmp->next_;
  }
}

int log_add_target(const char* conf)
{
  if(!conf)
    return -1;

  int ret = log_targets_add(&stdlog.targets_, conf);
  if(!ret) update_max_prio();
  return ret;
}

void log_printf(log_prio_t prio, const char* fmt, ...)
{
  if(stdlog.max_prio_ < prio)
    return;

  static char msg[MSG_LENGTH_MAX];
  va_list args;

  va_start(args, fmt);
  vsnprintf(msg, MSG_LENGTH_MAX, fmt, args);
  va_end(args);

  log_targets_log(&stdlog.targets_, prio, msg);
}

void log_print_hex_dump(log_prio_t prio, const u_int8_t* buf, u_int32_t len)
{
  if(stdlog.max_prio_ < prio)
    return;

  static char msg[MSG_LENGTH_MAX];

  if(!buf) {
    snprintf(msg, MSG_LENGTH_MAX, "(NULL)");
  }
  else {
    u_int32_t i;
    int offset = snprintf(msg, MSG_LENGTH_MAX, "dump(%d): ", len);
    if(offset < 0)
      return;
    u_int8_t* ptr = &msg[offset];
    
    for(i=0; i < len; i++) {
      if(((i+1)*3) >= (MSG_LENGTH_MAX - offset))
        break;
      snprintf(ptr, 3, "%02X ", buf[i]);
      ptr+=3;
    }
  }
  log_targets_log(&stdlog.targets_, prio, msg);
}
