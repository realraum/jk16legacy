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

#include "datatypes.h"

#include "options.h"

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <ctype.h>
#include <errno.h>

#include "log.h"

#define PARSE_BOOL_PARAM(SHORT, LONG, VALUE)             \
    else if(!strcmp(str,SHORT) || !strcmp(str,LONG))     \
      VALUE = 1;

#define PARSE_INVERSE_BOOL_PARAM(SHORT, LONG, VALUE)     \
    else if(!strcmp(str,SHORT) || !strcmp(str,LONG))     \
      VALUE = 0;

#define PARSE_INT_PARAM(SHORT, LONG, VALUE)              \
    else if(!strcmp(str,SHORT) || !strcmp(str,LONG))     \
    {                                                    \
      if(argc < 1)                                       \
        return i;                                        \
      VALUE = atoi(argv[i+1]);                           \
      argc--;                                            \
      i++;                                               \
    }

#define PARSE_STRING_PARAM(SHORT, LONG, VALUE)           \
    else if(!strcmp(str,SHORT) || !strcmp(str,LONG))     \
    {                                                    \
      if(argc < 1 || argv[i+1][0] == '-')                \
        return i;                                        \
      if(VALUE) free(VALUE);                             \
      VALUE = strdup(argv[i+1]);                         \
      if(!VALUE)                                         \
        return -2;                                       \
      argc--;                                            \
      i++;                                               \
    }

#define PARSE_STRING_PARAM_SEC(SHORT, LONG, VALUE)       \
    else if(!strcmp(str,SHORT) || !strcmp(str,LONG))     \
    {                                                    \
      if(argc < 1 || argv[i+1][0] == '-')                \
        return i;                                        \
      if(VALUE) free(VALUE);                             \
      VALUE = strdup(argv[i+1]);                         \
      if(!VALUE)                                         \
        return -2;                                       \
      size_t j;                                          \
      for(j=0; j < strlen(argv[i+1]); ++j)               \
        argv[i+1][j] = '#';                              \
      argc--;                                            \
      i++;                                               \
    }

#define PARSE_HEXSTRING_PARAM_SEC(SHORT, LONG, VALUE)    \
    else if(!strcmp(str,SHORT) || !strcmp(str,LONG))     \
    {                                                    \
      if(argc < 1 || argv[i+1][0] == '-')                \
        return i;                                        \
      int ret;                                           \
      ret = options_parse_hex_string(argv[i+1], &VALUE); \
      if(ret > 0)                                        \
        return i+1;                                      \
      else if(ret < 0)                                   \
        return ret;                                      \
      size_t j;                                          \
      for(j=0; j < strlen(argv[i+1]); ++j)               \
        argv[i+1][j] = '#';                              \
      argc--;                                            \
      i++;                                               \
    }

#define PARSE_STRING_LIST(SHORT, LONG, LIST)             \
    else if(!strcmp(str,SHORT) || !strcmp(str,LONG))     \
    {                                                    \
      if(argc < 1 || argv[i+1][0] == '-')                \
        return i;                                        \
      int ret = string_list_add(&LIST, argv[i+1]);       \
      if(ret == -2)                                      \
        return ret;                                      \
      else if(ret)                                       \
        return i+1;                                      \
      argc--;                                            \
      i++;                                               \
    }

#define PARSE_KEY_VALUE(SHORT, LONG, SEP, KV)            \
    else if(!strcmp(str,SHORT) || !strcmp(str,LONG))     \
    {                                                    \
      if(argc < 1 || argv[i+1][0] == '-')                \
        return i;                                        \
      char* value = strchr(argv[i+1], SEP);              \
      if(!value || value[1] == 0)                        \
        return i+1;                                      \
      value[0] = 0;                                      \
      value++;                                           \
      if(key_value_storage_add(&KV, argv[i+1], value))   \
        return -2;                                       \
      argc--;                                            \
      i++;                                               \
    }

int options_parse_hex_string(const char* hex, buffer_t* buffer)
{
  if(!hex || !buffer)
    return -1;

  u_int32_t hex_len = strlen(hex);
  if(hex_len%2)
    return 1;

  if(buffer->buf_) 
    free(buffer->buf_);
  
  buffer->length_ = hex_len/2;
  buffer->buf_ = malloc(buffer->length_);
  if(!buffer->buf_) {
    buffer->length_ = 0;
    return -2;
  }

  const char* ptr = hex;
  int i;
  for(i=0;i<buffer->length_;++i) {
    u_int32_t tmp;
    sscanf(ptr, "%2X", &tmp);
    buffer->buf_[i] = (u_int8_t)tmp;
    ptr += 2;
  }

  return 0;
}



int options_parse(options_t* opt, int argc, char* argv[])
{
  if(!opt)
    return -1;

  options_default(opt);

  if(opt->progname_)
    free(opt->progname_);
  opt->progname_ = strdup(argv[0]);
  if(!opt->progname_)
    return -2;

  argc--;

  int i;
  for(i=1; argc > 0; ++i)
  {
    char* str = argv[i];
    argc--;

    if(!strcmp(str,"-h") || !strcmp(str,"--help"))
      return -1;
    PARSE_INVERSE_BOOL_PARAM("-D","--nodaemonize", opt->daemonize_)
    PARSE_STRING_PARAM("-u","--username", opt->username_)
    PARSE_STRING_PARAM("-g","--groupname", opt->groupname_)
    PARSE_STRING_PARAM("-C","--chroot", opt->chroot_dir_)
    PARSE_STRING_PARAM("-P","--write-pid", opt->pid_file_)
    PARSE_STRING_LIST("-L","--log", opt->log_targets_)
    PARSE_STRING_PARAM("-d","--device", opt->tty_dev_)
    PARSE_STRING_PARAM("-s","--socket", opt->command_sock_)
    PARSE_STRING_PARAM("-p","--powerid-file", opt->powerid_file_)
    PARSE_STRING_PARAM("-a","--sampledev-file", opt->sampledev_file_)
    PARSE_KEY_VALUE("-A","--autosampledev", ',', opt->autosampledevs_)
    else 
      return i;
  }

  return 0;
}


int options_parse_key_value_file(const char* filename, key_value_storage_t* storage)
{
  FILE* file = fopen(filename, "r");
  if(file) {
    char buf[100];
    while(fgets(buf, 100, file) != NULL) {
      char* tmp, *key, *value;
      for(tmp = buf;*tmp == ' '; ++tmp);
      if(*(key = tmp) == 0) continue;
      for(;*tmp != ' ' && *tmp != 0;++tmp);
      if(*tmp == 0) continue;
      *tmp=0;
      ++tmp;
      for(;*tmp == ' ';++tmp);
      if(*(value = tmp) == 0) continue;
      for(;*tmp != ' ' && *tmp != 0 && *tmp != '\n';++tmp);
      *tmp = 0;
      
      if(key_value_storage_add(storage, key, value))
        return -2;
    }
    fclose(file);
  }
  else {
    log_printf(ERROR,"unable to open conf file (%s): %s", filename, strerror(errno));
    return -1;
  }
}

int options_parse_post(options_t* opt)
{
  if(!opt)
    return -1;

  if(opt->powerid_file_) {
    int ret = options_parse_key_value_file(opt->powerid_file_, &opt->powerids_);
    if(ret)
      return ret;
  }

  if(opt->sampledev_file_) {
    int ret = options_parse_key_value_file(opt->sampledev_file_, &opt->sampledevs_);
    if(ret)
      return ret;
  }

  string_list_element_t* k = opt->autosampledevs_.keys_.first_;
  string_list_element_t* v = opt->autosampledevs_.values_.first_;
  while(k && v) {
    if(!key_value_storage_find(&opt->sampledevs_, k->string_)) {
      log_printf(ERROR, "sample dev '%s' not in file '%s'", k->string_, opt->sampledev_file_);
      return -1;
    }
    if(atoi(v->string_) <= 0) {
      log_printf(ERROR, "invalid rate '%s' for sample dev '%s'", v->string_, k->string_);
      return -1;
    }
    k = k->next_;
    v = v->next_;
  }
  
  return 0;
}

void options_default(options_t* opt)
{
  if(!opt)
    return;

  opt->progname_ = strdup("powersensordaemon");
  opt->daemonize_ = 1;
  opt->username_ = NULL;
  opt->groupname_ = NULL;
  opt->chroot_dir_ = NULL;
  opt->pid_file_ = NULL;
  string_list_init(&opt->log_targets_);

  opt->tty_dev_ = strdup("/dev/ttyUSB0");
  opt->command_sock_ = strdup("/var/run/powersensordaemon/cmd.sock");
  opt->powerid_file_ = NULL;
  key_value_storage_init(&opt->powerids_);
  opt->sampledev_file_ = NULL;
  key_value_storage_init(&opt->sampledevs_);
  key_value_storage_init(&opt->autosampledevs_);
}

void options_clear(options_t* opt)
{
  if(!opt)
    return;

  if(opt->progname_)
    free(opt->progname_);
  if(opt->username_)
    free(opt->username_);
  if(opt->groupname_)
    free(opt->groupname_);
  if(opt->chroot_dir_)
    free(opt->chroot_dir_);
  if(opt->pid_file_)
    free(opt->pid_file_);
  string_list_clear(&opt->log_targets_);

  if(opt->tty_dev_)
    free(opt->tty_dev_);
  if(opt->command_sock_)
    free(opt->command_sock_);
  if(opt->powerid_file_)
    free(opt->powerid_file_);
  key_value_storage_clear(&opt->powerids_);
  if(opt->sampledev_file_)
    free(opt->sampledev_file_);
  key_value_storage_clear(&opt->sampledevs_);
  key_value_storage_clear(&opt->autosampledevs_);
}

void options_print_usage()
{
  printf("USAGE:\n");
  printf("powersensordaemon [-h|--help]                         prints this...\n");
  printf("            [-D|--nodaemonize]                  don't run in background\n");
  printf("            [-u|--username] <username>          change to this user\n");
  printf("            [-g|--groupname] <groupname>        change to this group\n");
  printf("            [-C|--chroot] <path>                chroot to this directory\n");
  printf("            [-P|--write-pid] <path>             write pid to this file\n");
  printf("            [-L|--log] <target>:<level>[,<param1>[,<param2>..]]\n");
  printf("                                                add a log target, can be invoked several times\n");

  printf("            [-d|--device] <tty device>          the device file e.g. /dev/ttyUSB0\n");
  printf("            [-s|--command-sock] <unix sock>     the command socket e.g. /var/run/powersensordaemon/cmd.sock\n");
  printf("            [-p|--powerid-file] <path>          file that contains the power ids\n");
  printf("            [-a|--sampledev-file] <path>        file that contains all sample devices\n");
  printf("            [-A|--autosampledev] <device>,<delay between samples in seconds>\n");
  printf("                                                automatic sample this devices, can be invoked several times\n");
}

void options_print(options_t* opt)
{
  if(!opt)
    return;

  printf("progname: '%s'\n", opt->progname_);
  printf("daemonize: %d\n", opt->daemonize_);
  printf("username: '%s'\n", opt->username_);
  printf("groupname: '%s'\n", opt->groupname_);
  printf("chroot_dir: '%s'\n", opt->chroot_dir_);
  printf("pid_file: '%s'\n", opt->pid_file_);
  printf("log_targets: \n");
  string_list_print(&opt->log_targets_, "  '", "'\n");

  printf("tty_dev: '%s'\n", opt->tty_dev_);
  printf("command_sock: '%s'\n", opt->command_sock_);
  printf("powerid_file: '%s'\n", opt->powerid_file_);
  printf("powerids: \n");
  key_value_storage_print(&opt->powerids_, "  '", "' -> '", "'\n");
  printf("sampledev_file: '%s'\n", opt->sampledev_file_);
  printf("sampledevs: \n");
  key_value_storage_print(&opt->sampledevs_, "  '", "' -> '", "'\n");
  printf("autosampledevs: \n");
  key_value_storage_print(&opt->autosampledevs_, "  '", "' -> '", "'\n");
}
