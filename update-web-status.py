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
lh_syslog.setFormatter(logging.Formatter('update-web-status.py: %(levelname)s %(message)s'))
logger.addHandler(lh_syslog)
lh_stderr = logging.StreamHandler()
logger.addHandler(lh_stderr)

class UWSConfig:
  def __init__(self,configfile=None):
    self.configfile=configfile
    self.config_parser=ConfigParser.ConfigParser()
    self.config_parser.add_section('web')
    self.config_parser.set('web','cgiuri','https://www.realraum.at/cgi/status.cgi?pass=jako16&set=')
    self.config_parser.set('web','htmlopen','<html><body bgcolor="lime"><center><b>T&uuml;r ist Offen</b></center></body></html>')
    self.config_parser.set('web','htmlclosed','<html><body bgcolor="red"><b><center>T&uuml;r ist Geschlossen</center></b></body></html>')
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
    
  def checkConfigUpdates(self):
    global logger
    if self.configfile is None:
      return
    logging.debug("Checking Configfile mtime: "+self.configfile)
    try:
      mtime = os.path.getmtime(self.configfile)
    except IOError:
      return
    if self.config_mtime < mtime:
      logging.debug("Reading Configfile")
      try:
        self.config_parser.read(self.configfile)
        self.config_mtime=os.path.getmtime(self.configfile)
      except ConfigParser.ParsingError, pe_ex:
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

def touchURL(url):
  try:
    f = urllib.urlopen(url)
    rq_response = f.read()
    logging.debug("touchURL: Response "+rq_response)
    f.close()
    return rq_response
  except Exception, e:
    logging.error("touchURL: "+str(e))

def setRealraumHtmlStatus(htmlcode):
  htmlcode_escaped = re.sub(r'[^\x30-\x39\x41-\x7E]',lambda m:"%%%x"%ord(m.group(0)),htmlcode)
  if touchURL(uwscfg.web_cgiuri + htmlcode_escaped) != htmlcode:
    logging.error("setRealraumHtmlStatus: Error setting Status, Output does not match Input")
  
def displayOpen():
  setRealraumHtmlStatus(uwscfg.web_htmlopen)
  
def displayClosed():
  setRealraumHtmlStatus(uwscfg.web_htmlclosed)
  
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

logging.info("Door Status Listener started")

if len(sys.argv) > 1:
  socketfile = sys.argv[1]
else:
  socketfile = "/var/run/tuer/door_cmd.socket"
  
if len(sys.argv) > 2:
  uwscfg = UWSConfig(sys.argv[2])
else:
  uwscfg = UWSConfig()

#socket.setdefaulttimeout(10.0) #affects all new Socket Connections (urllib as well)
sockhandle = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
RE_STATUS = re.compile(r'Status: (\w+), idle')
RE_REQUEST = re.compile(r'Request: (\w+) (?:Card )?(.+)')
RE_ERROR = re.compile(r'Error: (.+)')
while True:
  try:
    sockhandle.connect(socketfile)
    conn = os.fdopen(sockhandle.fileno())
    sockhandle.send("listen\n")
    sockhandle.send("status\n")
    while True:
      line = conn.readline()
      logging.debug("Got Line: " + line)
      
      uwscfg.checkConfigUpdates()
      
      m = RE_STATUS.match(line)
      if not m is None:
        status = m.group(1)
        if status == "opened":
          displayOpen()
        if status == "closed":
          displayClosed()
      #~ m = RE_REQUEST.match(line)
      #~ if not m is None:  
        #~ #(rq_action,rq_by) = m.group(1,2)
        #~ action_by = " von " + m.group(2)
      #~ else:
        #~ action_by = ""
      #~ m = RE_ERROR.match(line)
      #~ if not m is None:
        #~ errorstr = m.group(1)
        #~ #handle Error
  except Exception, ex:
    logging.error("main: "+str(ex)) 
    try:
      conn.close()
    except:
      pass
    try:
      sockhandle.close()
    except:
      pass
    time.sleep(5)

