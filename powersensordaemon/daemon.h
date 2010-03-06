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

#ifndef UANYTUN_daemon_h_INCLUDED
#define UANYTUN_daemon_h_INCLUDED

#include <poll.h>
#include <fcntl.h>
#include <pwd.h>
#include <grp.h>
#include <sys/wait.h>
#include <sys/stat.h>
#include <unistd.h>

struct priv_info_struct {
  struct passwd* pw_;
  struct group* gr_;
};
typedef struct priv_info_struct priv_info_t;

int priv_init(priv_info_t* priv, const char* username, const char* groupname)
{
  if(!priv)
    return -1;

  priv->pw_ = NULL;
  priv->gr_ = NULL;

  priv->pw_ = getpwnam(username);
  if(!priv->pw_) {
    log_printf(ERROR, "unkown user %s", username);
    return -1;
  }

  if(groupname)
    priv->gr_ = getgrnam(groupname);
  else
    priv->gr_ = getgrgid(priv->pw_->pw_gid);

  if(!priv->gr_) {
    log_printf(ERROR, "unkown group %s", groupname);
    return -1;
  }

  return 0;
}

int priv_drop(priv_info_t* priv)
{
  if(!priv || !priv->pw_ || !priv->gr_) {
    log_printf(ERROR, "privileges not initialized properly");
    return -1;
  }

  if(setgid(priv->gr_->gr_gid))  {
    log_printf(ERROR, "setgid('%s') failed: %s", priv->gr_->gr_name, strerror(errno));
    return -1;
  }

  gid_t gr_list[1];
  gr_list[0] = priv->gr_->gr_gid;
  if(setgroups (1, gr_list)) {
    log_printf(ERROR, "setgroups(['%s']) failed: %s", priv->gr_->gr_name, strerror(errno));
    return -1;
  }

  if(setuid(priv->pw_->pw_uid)) {
    log_printf(ERROR, "setuid('%s') failed: %s", priv->pw_->pw_name, strerror(errno));
    return -1;
  }

  log_printf(NOTICE, "dropped privileges to %s:%s", priv->pw_->pw_name, priv->gr_->gr_name);
  return 0;
}


int do_chroot(const char* chrootdir)
{
  if(getuid() != 0) {
    log_printf(ERROR, "this programm has to be run as root in order to run in a chroot");
    return -1;
  }

  if(chroot(chrootdir)) {
    log_printf(ERROR, "can't chroot to %s: %s", chrootdir, strerror(errno));
    return -1;
  }
  log_printf(NOTICE, "we are in chroot jail (%s) now", chrootdir);
  if(chdir("/")) {
    log_printf(ERROR, "can't change to /: %s", strerror(errno));
    return -1;
  }
}

void daemonize()
{
  pid_t pid;

  pid = fork();
  if(pid < 0) {
    log_printf(ERROR, "daemonizing failed at fork(): %s, exitting", strerror(errno));
    exit(-1);
  }
  if(pid) exit(0);

  umask(0);

  if(setsid() < 0) {
    log_printf(ERROR, "daemonizing failed at setsid(): %s, exitting", strerror(errno));
    exit(-1);
  }

  pid = fork();
  if(pid < 0) {
    log_printf(ERROR, "daemonizing failed at fork(): %s, exitting", strerror(errno));
    exit(-1);
  }
  if(pid) exit(0);

  if ((chdir("/")) < 0) {
    log_printf(ERROR, "daemonizing failed at chdir(): %s, exitting", strerror(errno));
    exit(-1);
  }

  int fd;
  for (fd=0;fd<=2;fd++) // close all file descriptors
    close(fd);
  fd = open("/dev/null",O_RDWR);        // stdin
  if(fd == -1)
    log_printf(WARNING, "can't open stdin (chroot and no link to /dev/null?)");
  else {
    if(dup(fd) == -1)   // stdout
      log_printf(WARNING, "can't open stdout");
    if(dup(fd) == -1)   // stderr
      log_printf(WARNING, "can't open stderr");
  }
  umask(027);
}

#endif

