#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import os.path
import sys
#import threading
import logging
import logging.handlers
import urllib
import time
import signal
import re
import socket
import subprocess
import types
import ConfigParser
import traceback

logger = logging.getLogger()
logger.setLevel(logging.INFO)
lh_syslog = logging.handlers.SysLogHandler(address="/dev/log",facility=logging.handlers.SysLogHandler.LOG_LOCAL2)
lh_syslog.setFormatter(logging.Formatter('play-sound-status.py: %(levelname)s %(message)s'))
logger.addHandler(lh_syslog)
lh_stderr = logging.StreamHandler()
logger.addHandler(lh_stderr)

class UWSConfig:
  def __init__(self,configfile=None):
    self.configfile=configfile
    self.config_parser=ConfigParser.ConfigParser()
    self.config_parser.add_section('playsound')
    self.config_parser.set('playsound','remote_cmd',"ssh -i /flash/tuer/id_rsa -o PasswordAuthentication=no -o StrictHostKeyChecking=no %RHOST% %RSHELL%")
    self.config_parser.set('playsound','remote_host',"root@slug.realraum.at")
    self.config_parser.set('playsound','remote_shell',"/home/playmp3.sh /home/half-life-door.mp3")
    self.config_parser.set('playsound','delay',"3.0")
    self.config_parser.add_section('debug')
    self.config_parser.set('debug','enabled',"False")
    self.config_parser.add_section('tracker')
    self.config_parser.set('tracker','socket',"/var/run/tuer/presence.socket")    
    self.config_mtime=0
    if not self.configfile is None:
      try:
        cf_handle = open(self.configfile,"r")
        cf_handle.close()
      except IOError:
        self.writeConfigFile()
      else:
        self.checkConfigUpdates()
    
  def checkConfigUpdates(self):
    global logger
    if self.configfile is None:
      return
    logging.debug("Checking Configfile mtime: "+self.configfile)
    try:
      mtime = os.path.getmtime(self.configfile)
    except (IOError,OSError):
      return
    if self.config_mtime < mtime:
      logging.debug("Reading Configfile")
      try:
        self.config_parser.read(self.configfile)
        self.config_mtime=os.path.getmtime(self.configfile)
      except (ConfigParser.ParsingError, IOError), pe_ex:
        logging.error("Error parsing Configfile: "+str(pe_ex))
      if self.config_parser.get('debug','enabled') == "True":
        logger.setLevel(logging.DEBUG)
      else:
        logger.setLevel(logging.INFO)

  def writeConfigFile(self):
    if self.configfile is None:
      return
    logging.debug("Writing Configfile "+self.configfile)      
    try:
      cf_handle = open(self.configfile,"w")
      self.config_parser.write(cf_handle)
      cf_handle.close()
      self.config_mtime=os.path.getmtime(self.configfile)
    except IOError, io_ex:
      logging.error("Error writing Configfile: "+str(io_ex))
      self.configfile=None

  def __getattr__(self, name):
    underscore_pos=name.find('_')
    if underscore_pos < 0:
      raise AttributeError
    try:
      return self.config_parser.get(name[0:underscore_pos], name[underscore_pos+1:])
    except (ConfigParser.NoOptionError, ConfigParser.NoSectionError):
      raise AttributeError



def playRemoteSound():
  global sshp,uwscfg
  uwscfg.checkConfigUpdates()
  sshp = None
  try:
    cmd = uwscfg.playsound_remote_cmd.replace("%RHOST%",uwscfg.playsound_remote_host).replace("%RSHELL%",uwscfg.playsound_remote_shell).split(" ")
    logging.debug("playRemoteSound: Executing: "+" ".join(cmd))
    sshp = subprocess.Popen(cmd, bufsize=1024, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False)
    logging.debug("playRemoteSound: pid %d: running=%d" % (sshp.pid,sshp.poll() is None))
    if not sshp.poll() is None:
      raise Exception("playRemoteSound: subprocess %d not started ?, returncode: %d" % (sshp.pid,sshp.returncode))
  except Exception, ex:
    logging.error("playRemoteSound: "+str(ex)) 
    traceback.print_exc(file=sys.stdout)
    if not sshp is None and sshp.poll() is None:
      if sys.hexversion >= 0x020600F0:
        sshp.terminate()
      else:
        subprocess.call(["kill",str(sshp.pid)])
      time.sleep(1.5)
      if sshp.poll() is None:
        logging.error("playRemoteSound: subprocess still alive, sending SIGKILL to pid %d" % (sshp.pid))
        if sys.hexversion >= 0x020600F0:
          sshp.kill()
        else:
          subprocess.call(["kill","-9",str(sshp.pid)])
    time.sleep(5)  



def popenTimeout1(cmd, pinput, returncode_ok=[0], ptimeout = 20.0, pcheckint = 0.25):
  logging.debug("popenTimeout1: starting: " + cmd)
  try:
    sppoo = subprocess.Popen(cmd, stdin=subprocess.PIPE, shell=True)
    sppoo.communicate(input=pinput)
    timeout_counter=ptimeout
    while timeout_counter > 0:
      time.sleep(pcheckint)
      timeout_counter -= pcheckint
      if not sppoo.poll() is None:
        logging.debug("popenTimeout2: subprocess %d finished, returncode: %d" % (sppoo.pid,sppoo.returncode))
        return (sppoo.returncode in returncode_ok)
    #timeout reached
    logging.error("popenTimeout1: subprocess took too long (>%fs), sending SIGTERM to pid %d" % (ptimeout,sppoo.pid))
    if sys.hexversion >= 0x020600F0:
      sppoo.terminate()
    else:
      subprocess.call(["kill",str(sppoo.pid)])
    time.sleep(1.0)
    if sppoo.poll() is None:
      logging.error("popenTimeout1: subprocess still alive, sending SIGKILL to pid %d" % (sppoo.pid))
      if sys.hexversion >= 0x020600F0:
        sppoo.kill()
      else:
        subprocess.call(["kill","-9",str(sppoo.pid)])
    return False
  except Exception, e:
    logging.error("popenTimeout1: "+str(e))
    return False
  
def popenTimeout2(cmd, pinput, returncode_ok=[0], ptimeout=21):
  logging.debug("popenTimeout2: starting: " + cmd)
  try:
    sppoo = subprocess.Popen(cmd, stdin=subprocess.PIPE, shell=True)
    if sys.hexversion >= 0x020600F0:
      old_shandler = signal.signal(signal.SIGALRM,lambda sn,sf: sppoo.kill())
    else:
      old_shandler = signal.signal(signal.SIGALRM,lambda sn,sf: os.system("kill -9 %d" % sppoo.pid))
    signal.alarm(ptimeout) #schedule alarm
    sppoo.communicate(input=pinput)
    sppoo.wait()
    signal.alarm(0) #disable pending alarms
    signal.signal(signal.SIGALRM, old_shandler) 
    logging.debug("popenTimeout2: subprocess %d finished, returncode: %d" % (sppoo.pid,sppoo.returncode))
    if sppoo.returncode < 0:
      logging.error("popenTimeout2: subprocess took too long (>%ds) and pid %d was killed" % (ptimeout,sppoo.pid))
    return (sppoo.returncode in returncode_ok)
  except Exception, e:
    logging.error("popenTimeout2: "+str(e))
    try:
      signal.signal(signal.SIGALRM, old_shandler) 
    except:
      pass
    return False

def exitHandler(signum, frame):
  logging.info("Update-Web-Status stopping")
  try:
    conn.close()
  except:
    pass
  try:
    sockhandle.close()
  except:
    pass
  sys.exit(0)
  
#signals proapbly don't work because of readline
#signal.signal(signal.SIGTERM, exitHandler)
signal.signal(signal.SIGINT, exitHandler)
signal.signal(signal.SIGQUIT, exitHandler)

logging.info("Door Status Listener 'PlaySound' started")

if len(sys.argv) > 1:
  uwscfg = UWSConfig(sys.argv[1])
else:
  uwscfg = UWSConfig()

#socket.setdefaulttimeout(10.0) #affects all new Socket Connections (urllib as well)
RE_PRESENCE = re.compile(r'Presence: (yes|no)(?:, (opened|closed), (.+))?')
RE_BUTTON = re.compile(r'PanicButton|button\d?')
while True:
  try:
    if not os.path.exists(uwscfg.tracker_socket):
      logging.debug("Socketfile '%s' not found, waiting 5 secs" % uwscfg.tracker_socket)
      time.sleep(5)
      continue
    sockhandle = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sockhandle.connect(uwscfg.tracker_socket)
    conn = os.fdopen(sockhandle.fileno())
    #sockhandle.send("listen\n")
    #sockhandle.send("status\n")
    last_status=None
    unixts_panic_button=None
    while True:
      line = conn.readline()
      logging.debug("Got Line: " + line)
      
      uwscfg.checkConfigUpdates()
      
      if line == "":
        raise Exception("EOF on Socket, daemon seems to have quit")
      
      m = RE_PRESENCE.match(line)
      if not m is None:
        status = m.group(1)
        last_status=(status == "yes")
        unixts_panic_button=None
        if last_status:
          time.sleep(float(uwscfg.playsound_delay))
          playRemoteSound()
        continue
        
      m = RE_BUTTON.match(line)
      if not m is None:
        pass  #insert panic action here
        continue
                
  except Exception, ex:
    logging.error("main: "+str(ex)) 
    try:
      sockhandle.close()
    except:
      pass
    conn=None
    sockhandle=None      
    time.sleep(5)
