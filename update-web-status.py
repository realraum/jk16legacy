#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import os.path
import sys
#import threading
import logging
import urllib
import time
import signal
import re
import socket
import subprocess
import types
import ConfigParser

logging.basicConfig(
  level=logging.INFO,
  #level=logging.ERROR,
  #level=logging.DEBUG,
  filename='/var/log/tmp/update-web-status.log',
  format="%(asctime)s %(message)s",
  datefmt="%Y-%m-%d %H:%M"
  )

class UWSConfig:
  def __init__(self,configfile=None):
    self.configfile=configfile
    self.config_parser=ConfigParser.ConfigParser()
    self.config_parser.add_section('url')
    self.config_parser.set('url','open','https://www.realraum.at/cgi/status.cgi?pass=jako16&set=%3Chtml%3E%3Cbody%20bgcolor=%22lime%22%3E%3Ccenter%3E%3Cb%3ET%26uuml%3Br%20ist%20Offen%3C/b%3E%3C/center%3E%3C/body%3E%3C/html%3E')
    self.config_parser.set('url','closed','https://www.realraum.at/cgi/status.cgi?pass=jako16&set=%3Chtml%3E%3Cbody%20bgcolor=%22red%22%3E%3Cb%3E%3Ccenter%3ET%26uuml%3Br%20ist%20Geschlossen%3C/center%3E%3C/b%3E%3C/body%3E%3C/html%3E')
    self.config_parser.add_section('xmpp')
    self.config_parser.set('xmpp','recipients_debug','xro@jabber.tittelbach.at')
    self.config_parser.set('xmpp','recipients_normal','xro@jabber.tittelbach.at otti@wirdorange.org')
    self.config_parser.set('xmpp','recipients_nooffline','the-equinox@jabber.org')
    self.config_parser.set('xmpp','msg_opened',"Realraum Tür wurde%s geöffnet")
    self.config_parser.set('xmpp','msg_closed',"Realraum Tür wurde%s geschlossen")
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



xmpp_msg_lastmsg = ""
action_by = ""
xmpp_firstmsg = True

def sendXmppMsg(recipients, msg, resource = "torwaechter", addtimestamp = True, noofflinemsg = False, ptimeout = 20.0, pcheckint = 0.5):
  if type(recipients) == types.ListType:
    recipients = " ".join(recipients)
  if type(recipients) == types.UnicodeType:
    recipients = recipients.decode("utf-8")
  if type(recipients) != types.StringType:
    raise Exception("argument recipients not a space separated string or xmpp addresses, can't send message")
  if recipients == "" or msg == "":
    return
  
  sendxmpp_cmd = "sendxmpp -u realrauminfo -p 5SPjTdub -j jabber.tittelbach.at -t "
  if resource:
    sendxmpp_cmd += "-r %s " % resource
  if noofflinemsg:
    sendxmpp_cmd += "--headline "
  sendxmpp_cmd += recipients
  
  if addtimestamp:
    msg += time.strftime(" (%Y-%m-%d %T)")
  
  logging.debug("Starting " + sendxmpp_cmd)
  try:
    sppoo = subprocess.Popen(sendxmpp_cmd, stdin=subprocess.PIPE, shell=True)
    sppoo.communicate(input=msg)
    while ptimeout > 0:
      time.sleep(pcheckint)
      ptimeout -= pcheckint
      if sppoo.poll():
        logging.debug("XMPPmessage sent: '%s'"  % msg)
        return
    #timeout reached
    logging.error("sendxmpp subprocess took too long (>%fs), sending SIGTERM to pid %d" % (ptimeout,sppoo.pid))
    sppoo.terminate()
    time.sleep(1.0)
    if sppoo.poll() is None:
      logging.error("sendxmpp subprocess still alive, sending SIGKILL to pid %d" % (sppoo.pid))
      sppoo.kill()
  except Exception, e:
    logging.error(str(e))
  
def distributeXmppMsg(msg,high_priority=False):
  global xmpp_firstmsg, xmpp_msg_lastmsg
  if xmpp_firstmsg:
    xmpp_msg_lastmsg = msg
    xmpp_firstmsg = False
  if msg != xmpp_msg_lastmsg:
    sendXmppMsg(uwscfg.xmpp_recipients_normal, msg)
    sendXmppMsg(uwscfg.xmpp_recipients_nooffline, msg, noofflinemsg=(not high_priority))
  else:
    sendXmppMsg(uwscfg.xmpp_recipients_debug, "D: " + msg)
  xmpp_msg_lastmsg = msg
  
def touchURL(url):
  try:
    f = urllib.urlopen(url)
    f.read()
    f.close()
  except Exception, e:
    logging.error(str(e))
  
def displayOpen():
  touchURL(uwscfg.url_open)
  distributeXmppMsg(uwscfg.xmpp_msg_opened % action_by)
  
def displayClosed():
  touchURL(uwscfg.url_closed)
  distributeXmppMsg(uwscfg.xmpp_msg_closed % action_by)
  
def exitHandler(signum, frame):
  logging.info("Door Status Listener stopping")
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

sendXmppMsg(uwscfg.xmpp_recipients_debug,"D: update-web-status.py started")

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
      m = RE_REQUEST.match(line)
      if not m is None:  
        #(rq_action,rq_by) = m.group(1,2)
        action_by = " von " + m.group(2)
      else:
        action_by = ""
      m = RE_ERROR.match(line)
      if not m is None:
        errorstr = m.group(1)
        if "too long!" in errorstr:
          distributeXmppMsg(uwscfg.xmpp_recipients_debug, "Door Error: "+errorstr, high_priority=True)
        else:
          sendXmppMsg(uwscfg.xmpp_recipients_debug, "D: Error: "+errorstr)
  except Exception, ex:
    logging.error(str(ex)) 
    try:
      conn.close()
    except:
      pass
    try:
      sockhandle.close()
    except:
      pass
    time.sleep(5)

