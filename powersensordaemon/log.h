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

#ifndef UANYTUN_log_h_INCLUDED
#define UANYTUN_log_h_INCLUDED

#define MSG_LENGTH_MAX 150

enum log_prio_enum { ERROR = 1, WARNING = 2, NOTICE = 3,
                     INFO = 4, DEBUG = 5 };
typedef enum log_prio_enum log_prio_t;

const char* log_prio_to_string(log_prio_t prio);

enum log_target_type_enum { TARGET_SYSLOG , TARGET_STDOUT, TARGET_STDERR, TARGET_FILE , TARGET_UNKNOWN };
typedef enum log_target_type_enum log_target_type_t;

struct log_target_struct {
  log_target_type_t type_;
  int (*init)(struct log_target_struct* self, const char* conf);
  void (*open)(struct log_target_struct* self);
  void (*log)(struct log_target_struct* self, log_prio_t prio, const char* msg);
  void (*close)(struct log_target_struct* self);
  void (*clear)(struct log_target_struct* self);
  int opened_;
  int enabled_;
  log_prio_t max_prio_;
  void* param_;
  struct log_target_struct* next_;
};
typedef struct log_target_struct log_target_t;


struct log_targets_struct {
  log_target_t* first_;
};
typedef struct log_targets_struct log_targets_t;

int log_targets_target_exists(log_targets_t* targets, log_target_type_t type);
int log_targets_add(log_targets_t* targets, const char* conf);
void log_targets_log(log_targets_t* targets, log_prio_t prio, const char* msg);
void log_targets_clear(log_targets_t* targets);


struct log_struct {
  log_prio_t max_prio_;
  log_targets_t targets_;
};
typedef struct log_struct log_t;

void log_init();
void log_close();
void update_max_prio();
int log_add_target(const char* conf);
void log_printf(log_prio_t prio, const char* fmt, ...);
void log_print_hex_dump(log_prio_t prio, const u_int8_t* buf, u_int32_t len);

#endif
