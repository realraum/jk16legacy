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

logger = logging.getLogger()
logger.setLevel(logging.INFO)
lh_syslog = logging.handlers.SysLogHandler(address="/dev/log",facility=logging.handlers.SysLogHandler.LOG_LOCAL2)
lh_syslog.setFormatter(logging.Formatter('switch-power.py: %(levelname)s %(message)s'))
logger.addHandler(lh_syslog)
lh_stderr = logging.StreamHandler()
logger.addHandler(lh_stderr)

class UWSConfig:
  def __init__(self,configfile=None):
    self.configfile=configfile
    self.config_parser=ConfigParser.ConfigParser()
    self.config_parser.add_section('slug')
    self.config_parser.set('slug','cgiuri','http://slug.realraum.at/cgi-bin/switch.cgi?id=%ID%&power=%ONOFF%')
    self.config_parser.set('slug','ids_present','logo werkzeug')
    self.config_parser.set('slug','ids_panic','idee schreibtisch labor werkzeug')
    self.config_parser.set('slug','ids_nonpresent_off','idee schreibtisch labor werkzeug stereo logo')
    self.config_parser.add_section('debug')
    self.config_parser.set('debug','enabled',"True")
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

def touchURL(url):
  try:
    f = urllib.urlopen(url)
    rq_response = f.read()
    logging.debug("touchURL: url: "+url)
    #logging.debug("touchURL: Response "+rq_response)
    f.close()
    return rq_response
  except Exception, e:
    logging.error("touchURL: "+str(e))

def switchPower(powerid,turn_on=False):
  if turn_on:
    onoff="on"
  else:
    onoff="off"
  touchURL(uwscfg.slug_cgiuri.replace("%ID%",powerid).replace("%ONOFF%",onoff))
  
def eventPresent():
  for id in uwscfg.slug_ids_present.split(" "):
    switchPower(id,True)

def eventNobodyHere():
  for id in uwscfg.slug_ids_nonpresent_off.split(" "):
    switchPower(id,False)

def eventPanic():
  lst1 = uwscfg.slug_ids_panic.split(" ")
  lst2 = lst1
  lst2.append(lst2.pop(0))
  #guarantee list has even number of elements by multiplying it with a factor of 2
  lst=zip(lst1,lst2) * 4
  lst2=None
  switchPower(lst[0][0],True)
  for (id1,id2) in lst: 
    switchPower(id2,True)
    time.sleep(0.3)
    switchPower(id1,False)
  time.sleep(0.6)
  for id in lst1:
    switchPower(id,False)

def exitHandler(signum, frame):
  logging.info("Power Switch Daemon stopping")
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

logging.info("Power Switch Daemon started")

if len(sys.argv) > 1:
  uwscfg = UWSConfig(sys.argv[1])
else:
  uwscfg = UWSConfig()

#socket.setdefaulttimeout(10.0) #affects all new Socket Connections (urllib as well)
RE_PRESENCE = re.compile(r'Presence: (yes|no)')
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
    while True:
      line = conn.readline()
      logging.debug("Got Line: " + line)
      
      uwscfg.checkConfigUpdates()
      
      if line == "":
        raise Exception("EOF on Socket, daemon seems to have quit")
      
      m = RE_PRESENCE.match(line)
      if not m is None:
        status = m.group(1)
        if status == "yes":
          eventPresent()
        else:
          eventNobodyHere()
        continue
      m = RE_BUTTON.match(line)
      if not m is None:
        eventPanic()
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
