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

#ifndef UANYTUN_log_targets_h_INCLUDED
#define UANYTUN_log_targets_h_INCLUDED

#include <time.h>

static char* get_time_formatted()
{
  char* time_string;
  time_t t = time(NULL);
  if(t < 0) 
    time_string = "<time read error>";
  else {
    time_string = ctime(&t);
    if(!time_string)
      time_string = "<time format error>";
    else {
      char* newline = strchr(time_string, '\n');
      if(newline)
        newline[0] = 0;
    }
  }
  return time_string;
}

enum syslog_facility_enum { USER = LOG_USER, MAIL = LOG_MAIL,
                            DAEMON = LOG_DAEMON, AUTH = LOG_AUTH,
                            SYSLOG = LOG_SYSLOG, LPR = LOG_LPR,
                            NEWS = LOG_NEWS, UUCP = LOG_UUCP,
                            CRON = LOG_CRON, AUTHPRIV = LOG_AUTHPRIV,
                            FTP = LOG_FTP, LOCAL0 = LOG_LOCAL0,
                            LOCAL1 = LOG_LOCAL1, LOCAL2 = LOG_LOCAL2,
                            LOCAL3 = LOG_LOCAL3, LOCAL4 = LOG_LOCAL4,
                            LOCAL5 = LOG_LOCAL5, LOCAL6 = LOG_LOCAL6,
                            LOCAL7 = LOG_LOCAL7 };
typedef enum syslog_facility_enum syslog_facility_t;

struct log_target_syslog_param_struct {
  char* logname_;
  syslog_facility_t facility_;
};
typedef struct log_target_syslog_param_struct log_target_syslog_param_t;

int log_target_syslog_init(log_target_t* self, const char* conf)
{
  if(!self || (conf && conf[0] == 0))
    return -1;
  
  self->param_ = malloc(sizeof(log_target_syslog_param_t));
  if(!self->param_)
    return -2;

  char* logname;
  const char* end = NULL;
  if(!conf)
    logname = strdup("uanytun");
  else {
    end = strchr(conf, ',');
    if(end) {
      size_t len = (size_t)(end - conf);
      if(!len) {
        free(self->param_);
        return -1;
      }  
      logname = malloc(len+1);
      if(logname) {
        strncpy(logname, conf, len);
        logname[len] = 0;
      }
    }
    else
      logname = strdup(conf);
  }

  if(!logname) {
    free(self->param_);
    return -2;
  }
  ((log_target_syslog_param_t*)(self->param_))->logname_ = logname;

  if(!end) {
    ((log_target_syslog_param_t*)(self->param_))->facility_ = DAEMON;
    return 0;
  }
  
  if(end[1] == 0 || end[1] == ',') {
    free(logname);
    free(self->param_);
    return -1;
  }
    
  const char* start = end + 1;
  end = strchr(start, ',');
  int i;
  for(i=0;;++i) {
    if(facilitynames[i].c_name == NULL) {
      free(logname);
      free(self->param_);
      return -1;
    }

    if(( end && !strncmp(start, facilitynames[i].c_name, (size_t)(end - start)) && facilitynames[i].c_name[(size_t)(end-start)] == 0) ||
       (!end && !strcmp(start, facilitynames[i].c_name))) {
        ((log_target_syslog_param_t*)(self->param_))->facility_ = facilitynames[i].c_val;
        break;
    }
  }

  return 0;
}

void log_target_syslog_open(log_target_t* self)
{
  if(!self || !self->param_)
    return;

  openlog(((log_target_syslog_param_t*)(self->param_))->logname_, LOG_PID, ((log_target_syslog_param_t*)(self->param_))->facility_);
  self->opened_ = 1;
}

void log_target_syslog_log(log_target_t* self, log_prio_t prio, const char* msg)
{
  if(!self || !self->param_ || !self->opened_)
    return;

  syslog((prio + 2) | ((log_target_syslog_param_t*)(self->param_))->facility_, "%s", msg);  
}

void log_target_syslog_close(log_target_t* self)
{
  closelog();
  self->opened_ = 0;
}

void log_target_syslog_clear(log_target_t* self)
{
  if(!self || !self->param_)
    return;

  if(((log_target_syslog_param_t*)(self->param_))->logname_)
    free(((log_target_syslog_param_t*)(self->param_))->logname_);

  free(self->param_);
}

log_target_t* log_target_syslog_new()
{
  log_target_t* tmp = malloc(sizeof(log_target_t));
  if(!tmp)
    return NULL;

  tmp->type_ = TARGET_SYSLOG;
  tmp->init = &log_target_syslog_init;
  tmp->open = &log_target_syslog_open;
  tmp->log = &log_target_syslog_log;
  tmp->close = &log_target_syslog_close;
  tmp->clear = &log_target_syslog_clear;
  tmp->opened_ = 0;
  tmp->enabled_ = 0;
  tmp->max_prio_ = NOTICE;
  tmp->param_ = NULL;
  tmp->next_ = NULL;

  return tmp;
}


struct log_target_file_param_struct {
  char* logfilename_;
  FILE* file_;
};
typedef struct log_target_file_param_struct log_target_file_param_t;

int log_target_file_init(log_target_t* self, const char* conf)
{
  if(!self || (conf && conf[0] == 0))
    return -1;
  
  self->param_ = malloc(sizeof(log_target_file_param_t));
  if(!self->param_)
    return -2;

  char* logfilename;
  if(!conf)
    logfilename = strdup("uanytun.log");
  else {
    const char* end = strchr(conf, ',');
    if(end) {
      size_t len = (size_t)(end - conf);
      if(!len) {
        free(self->param_);
        return -1;
      }  
      logfilename = malloc(len+1);
      if(logfilename) {
        strncpy(logfilename, conf, len);
        logfilename[len] = 0;
      }
    }
    else
      logfilename = strdup(conf);
  }

  if(!logfilename) {
    free(self->param_);
    return -2;
  }
  ((log_target_file_param_t*)(self->param_))->logfilename_ = logfilename;
  ((log_target_file_param_t*)(self->param_))->file_ = NULL;

  return 0;
}

void log_target_file_open(log_target_t* self)
{
  if(!self || !self->param_)
    return;

  ((log_target_file_param_t*)(self->param_))->file_ = fopen(((log_target_file_param_t*)(self->param_))->logfilename_, "w");
  if(((log_target_file_param_t*)(self->param_))->file_)
    self->opened_ = 1;
}

void log_target_file_log(log_target_t* self, log_prio_t prio, const char* msg)
{
  if(!self || !self->param_ || !self->opened_)
    return;

  fprintf(((log_target_file_param_t*)(self->param_))->file_, "%s %s: %s\n", get_time_formatted(), log_prio_to_string(prio), msg);
  fflush(((log_target_file_param_t*)(self->param_))->file_);
}

void log_target_file_close(log_target_t* self)
{
  if(!self || !self->param_)
    return;

  fclose(((log_target_file_param_t*)(self->param_))->file_);
  self->opened_ = 0;
}

void log_target_file_clear(log_target_t* self)
{
  if(!self || !self->param_)
    return;

  if(((log_target_file_param_t*)(self->param_))->logfilename_)
    free(((log_target_file_param_t*)(self->param_))->logfilename_);

  free(self->param_);
}


log_target_t* log_target_file_new()
{
  log_target_t* tmp = malloc(sizeof(log_target_t));
  if(!tmp)
    return NULL;

  tmp->type_ = TARGET_FILE;
  tmp->init = &log_target_file_init;
  tmp->open = &log_target_file_open;
  tmp->log = &log_target_file_log;
  tmp->close = &log_target_file_close;
  tmp->clear = &log_target_file_clear;
  tmp->opened_ = 0;
  tmp->enabled_ = 0;
  tmp->max_prio_ = NOTICE;
  tmp->param_ = NULL;
  tmp->next_ = NULL;

  return tmp;
}


void log_target_stdout_log(log_target_t* self, log_prio_t prio, const char* msg)
{
  printf("%s %s: %s\n", get_time_formatted(), log_prio_to_string(prio), msg);
}

log_target_t* log_target_stdout_new()
{
  log_target_t* tmp = malloc(sizeof(log_target_t));
  if(!tmp)
    return NULL;

  tmp->type_ = TARGET_STDOUT;
  tmp->init = NULL;
  tmp->open = NULL;
  tmp->log = &log_target_stdout_log;
  tmp->close = NULL;
  tmp->clear = NULL;
  tmp->opened_ = 0;
  tmp->enabled_ = 0;
  tmp->max_prio_ = NOTICE;
  tmp->param_ = NULL;
  tmp->next_ = NULL;

  return tmp;
}


void log_target_stderr_log(log_target_t* self, log_prio_t prio, const char* msg)
{
  fprintf(stderr, "%s %s: %s\n", get_time_formatted(), log_prio_to_string(prio), msg);
}

log_target_t* log_target_stderr_new()
{
  log_target_t* tmp = malloc(sizeof(log_target_t));
  if(!tmp)
    return NULL;

  tmp->type_ = TARGET_STDERR;
  tmp->init = NULL;
  tmp->open = NULL;
  tmp->log = &log_target_stderr_log;
  tmp->close = NULL;
  tmp->clear = NULL;
  tmp->opened_ = 0;
  tmp->enabled_ = 0;
  tmp->max_prio_ = NOTICE;
  tmp->param_ = NULL;
  tmp->next_ = NULL;

  return tmp;
}

#endif
