#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import with_statement
import os
import os.path
import sys
import threading
import logging
import logging.handlers
import time
import signal
import re
import socket
import select
import subprocess
import types
import ConfigParser
import traceback

logger = logging.getLogger()
logger.setLevel(logging.INFO)
lh_syslog = logging.handlers.SysLogHandler(address="/dev/log",facility=logging.handlers.SysLogHandler.LOG_LOCAL2)
lh_syslog.setFormatter(logging.Formatter('track-presence.py: %(levelname)s %(message)s'))
logger.addHandler(lh_syslog)
lh_stderr = logging.StreamHandler()
logger.addHandler(lh_stderr)

######## Config File Data Class ############

class UWSConfig:
  def __init__(self,configfile=None):
    #Synchronisation
    self.lock=threading.Lock()
    self.finished_reading=threading.Condition(self.lock)
    self.finished_writing=threading.Condition(self.lock)
    self.currently_reading=0
    self.currently_writing=False
    #Config Data
    self.configfile=configfile
    self.config_parser=ConfigParser.ConfigParser()
    self.config_parser.add_section('door')
    self.config_parser.set('door','cmd_socket',"/var/run/tuer/door_cmd.socket")
    self.config_parser.add_section('sensors')
    self.config_parser.set('sensors','remote_cmd',"ssh -o PasswordAuthentication=no %RHOST% %RSHELL% %RSOCKET%")
    self.config_parser.set('sensors','remote_host',"root@slug.realraum.at")
    self.config_parser.set('sensors','remote_socket',"/var/run/powersensordaemon/cmd.sock")
    self.config_parser.set('sensors','remote_shell',"usocket")
    self.config_parser.add_section('tracker')
    self.config_parser.set('tracker','sec_wait_movement_after_door_closed',2.5)
    self.config_parser.set('tracker','sec_general_movement_timeout',3600)
    self.config_parser.set('tracker','server_socket',"/var/run/tuer/presence.socket")
    self.config_parser.set('tracker','photo_flashlight',950)
    self.config_parser.set('tracker','photo_daylight',500)
    self.config_parser.set('tracker','photo_artif_light',150)
    self.config_parser.add_section('debug')
    self.config_parser.set('debug','enabled',"False")
    self.config_mtime=0
    if not self.configfile is None:
      try:
        cf_handle = open(self.configfile,"r")
        cf_handle.close()
      except IOError:
        self.writeConfigFile()
      else:
        self.checkConfigUpdates()
    
  def guardReading(self):
    self.lock.acquire()
    while self.currently_writing:
      self.finished_writing.wait()
    self.currently_reading+=1
    self.lock.release()

  def unguardReading(self):
    with self.lock:
      self.currently_reading-=1
      self.finished_reading.notifyAll()
      
  def guardWriting(self):
    with self.lock:
      self.currently_writing=True
      while self.currently_reading > 0:
        self.finished_reading.wait()
    
  def unguardWriting(self):
    with self.lock:
      self.currently_writing=False
      self.finished_writing.notifyAll()
    
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
      self.guardWriting()
      try:
        self.config_parser.read(self.configfile)
        self.config_mtime=os.path.getmtime(self.configfile)
      except (ConfigParser.ParsingError, IOError), pe_ex:
        logging.error("Error parsing Configfile: "+str(pe_ex))
      self.unguardWriting()
      self.guardReading()
      if self.config_parser.get('debug','enabled') == "True":
        logger.setLevel(logging.DEBUG)
      else:
        logger.setLevel(logging.INFO)
      self.unguardReading()

  def writeConfigFile(self):
    if self.configfile is None:
      return
    logging.debug("Writing Configfile "+self.configfile)
    self.guardReading()
    try:
      cf_handle = open(self.configfile,"w")
      self.config_parser.write(cf_handle)
      cf_handle.close()
      self.config_mtime=os.path.getmtime(self.configfile)
    except IOError, io_ex:
      logging.error("Error writing Configfile: "+str(io_ex))
      self.configfile=None
    self.unguardReading()

  def __getattr__(self, name):
    underscore_pos=name.find('_')
    if underscore_pos < 0:
      raise AttributeError
    rv=None
    self.guardReading()
    try:
      rv = self.config_parser.get(name[0:underscore_pos], name[underscore_pos+1:])
    except (ConfigParser.NoOptionError, ConfigParser.NoSectionError):
      self.unguardReading()
      raise AttributeError
    self.unguardReading()
    return rv


######## Status Listener Threads ############

def trackSensorStatusThread(uwscfg):
  try:
    cmd = uwscfg.sensors_remote_cmd.replace("%RHOST%",uwscfg.sensors_remote_host).replace("%RSHELL%",uwscfg.sensors_remote_shell).replace("%RSOCKET%",uwscfg.sensors_remote_socket).split(" ")
    print(cmd)
    sshp = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell=False)
    if not sshp.poll() is None:
      raise Exception("trackSensorStatusThread: subprocess %d finished, returncode: %d" % (sshp.pid,sshp.returncode))
    while True:
      if not sys.stdin is None:
        sys.stdout.write("> sample temp0")
        sshp.stdin.write("sample temp0\n")
      line=sshp.stdout.readline()
      if len(line) < 1:
        print "EOF on ssh"
        break
      else:
        print "> "+line
  except Exception, ex:
    logging.error("trackSensorStatusThread: "+str(ex)) 
    traceback.print_exc(file=sys.stdout)


############ Main Routine ############

def exitHandler(signum, frame):
  logging.info("Track Presence stopping")
  sys.exit(0)
  
#signals proapbly don't work because of readline
#signal.signal(signal.SIGTERM, exitHandler)
signal.signal(signal.SIGINT, exitHandler)
signal.signal(signal.SIGQUIT, exitHandler)

logging.info("Presence Tracker started")

#option and only argument: path to config file
if len(sys.argv) > 1:
  uwscfg = UWSConfig(sys.argv[1])
else:
  uwscfg = UWSConfig()

trackSensorStatusThread(uwscfg)
