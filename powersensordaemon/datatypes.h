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

#ifndef POWERSENSORDAEMON_datatypes_h_INCLUDED
#define POWERSENSORDAEMON_datatypes_h_INCLUDED

#include <stdint.h>
#include <arpa/inet.h>

typedef uint8_t u_int8_t;
typedef uint16_t u_int16_t;
typedef uint32_t u_int32_t;
typedef uint64_t u_int64_t;
/* typedef int8_t int8_t; */
/* typedef int16_t int16_t; */
/* typedef int32_t int32_t; */
/* typedef int64_t int64_t; */

struct buffer_struct {
  u_int32_t length_;
  u_int8_t* buf_;
};
typedef struct buffer_struct buffer_t;

struct read_buffer_struct {
  u_int32_t offset;
  u_int8_t buf[100];
};
typedef struct read_buffer_struct read_buffer_t;

#endif
