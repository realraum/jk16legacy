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

#include "log.h"
#include <signal.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/select.h>
#include <errno.h>

#include "sig_handler.h"

#include <stdio.h>


static int sig_pipe_fds[2];


static void sig_handler(int sig)
{
  sigset_t set;
  int ret = read(sig_pipe_fds[0], &set, sizeof(sigset_t));
  if(ret != sizeof(sigset_t))
    sigemptyset(&set);

  sigaddset(&set, sig);
  ret = write(sig_pipe_fds[1], &set, sizeof(sigset_t));
}


int signal_init()
{
  if(pipe(sig_pipe_fds)) {
    log_printf(ERROR, "signal handling init failed (pipe error: %s)", strerror(errno));
    return -1;
  }

  int i;
  for(i=0; i<2; ++i) {
    int fd_flags = fcntl(sig_pipe_fds[i], F_GETFL);
    if(fd_flags == -1) {
      log_printf(ERROR, "signal handling init failed (pipe fd[%d] read flags error: %s)", i, strerror(errno));
      return -1;
    }
    if(fcntl(sig_pipe_fds[i], F_SETFL, fd_flags | O_NONBLOCK) == -1){
      log_printf(ERROR, "signal handling init failed (pipe fd[%d] write flags error: %s)", i, strerror(errno));
      return -1;
    }
  }

  struct sigaction act, ign;
  act.sa_handler = sig_handler;
  sigfillset(&act.sa_mask);
  act.sa_flags = 0;
  ign.sa_handler = SIG_IGN;
  sigfillset(&ign.sa_mask);
  ign.sa_flags = 0;

  if((sigaction(SIGINT, &act, NULL) < 0) ||
     (sigaction(SIGQUIT, &act, NULL) < 0) ||
     (sigaction(SIGTERM, &act, NULL) < 0) ||
     (sigaction(SIGHUP, &act, NULL) < 0) ||
     (sigaction(SIGUSR1, &act, NULL) < 0) ||
     (sigaction(SIGUSR2, &act, NULL) < 0) ||
     (sigaction(SIGCHLD, &ign, NULL) < 0) ||
     (sigaction(SIGPIPE, &ign, NULL) < 0)) {

    log_printf(ERROR, "signal handling init failed (sigaction error: %s)", strerror(errno));
    close(sig_pipe_fds[0]);
    close(sig_pipe_fds[1]);
  }

  return sig_pipe_fds[0];
}

int signal_handle()
{
  sigset_t set, oldset, tmpset;

  sigemptyset(&tmpset);
  sigaddset(&tmpset, SIGINT);
  sigaddset(&tmpset, SIGQUIT);
  sigaddset(&tmpset, SIGTERM);
  sigaddset(&tmpset, SIGHUP);
  sigaddset(&tmpset, SIGUSR1);
  sigaddset(&tmpset, SIGUSR2);
  sigprocmask(SIG_BLOCK, &tmpset, &oldset);

  int ret = read(sig_pipe_fds[0], &set, sizeof(sigset_t));
  if(ret != sizeof(sigset_t))
    sigemptyset(&set);

  int return_value = 0;
  int sig;
  for(sig=1; sig < NSIG; ++sig) {
    if(sigismember(&set, sig)) {
      switch(sig) {
      case SIGINT: log_printf(NOTICE, "SIG-Int caught, exitting"); return_value = 1; break;
      case SIGQUIT: log_printf(NOTICE, "SIG-Quit caught, exitting"); return_value = 1; break;
      case SIGTERM: log_printf(NOTICE, "SIG-Term caught, exitting"); return_value = 1; break;
      case SIGHUP: log_printf(NOTICE, "SIG-Hup caught"); break;
      case SIGUSR1: log_printf(NOTICE, "SIG-Usr1 caught"); break;
      case SIGUSR2: log_printf(NOTICE, "SIG-Usr2 caught"); break;
      default: log_printf(WARNING, "unknown signal %d caught, ignoring", sig); break;
      }
      sigdelset(&set, sig);
    }
  }

  sigprocmask(SIG_SETMASK, &oldset, NULL);
  return return_value;
}

void signal_stop()
{
  struct sigaction act;
  act.sa_handler = SIG_DFL;
  sigemptyset(&act.sa_mask);
  act.sa_flags = 0;

  sigaction(SIGINT, &act, NULL);
  sigaction(SIGQUIT, &act, NULL);
  sigaction(SIGTERM, &act, NULL);
  sigaction(SIGHUP, &act, NULL);
  sigaction(SIGUSR1, &act, NULL);
  sigaction(SIGUSR2, &act, NULL);
  sigaction(SIGPIPE, &act, NULL);
  sigaction(SIGCHLD, &act, NULL);

  close(sig_pipe_fds[0]);
  close(sig_pipe_fds[1]);
}
