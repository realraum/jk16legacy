#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import os.path
import sys
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
#logger.setLevel(logging.DEBUG)
lh_syslog = logging.handlers.SysLogHandler(address="/dev/log",facility=logging.handlers.SysLogHandler.LOG_LOCAL2)
lh_syslog.setFormatter(logging.Formatter('update-xmpp-status.py: %(levelname)s %(message)s'))
logger.addHandler(lh_syslog)
lh_stderr = logging.StreamHandler()
logger.addHandler(lh_stderr)

class UWSConfig:
  def __init__(self,configfile=None):
    self.configfile=configfile
    self.config_parser=ConfigParser.ConfigParser()
    self.config_parser.add_section('xmpp')
    self.config_parser.set('xmpp','recipients_debug','xro@jabber.tittelbach.at')
    self.config_parser.set('xmpp','recipients_normal','xro@jabber.tittelbach.at otti@wirdorange.org')
    self.config_parser.set('xmpp','recipients_nooffline','the-equinox@jabber.org davrieb@jabber.ccc.de')
    self.config_parser.add_section('msg')
    self.config_parser.set('msg','bored',"The Button has been pressed ! Maybe somebody want's company. Go Visit !")
    self.config_parser.set('msg','present',"Somebodys presence has been detected${door_action_msg}")
    self.config_parser.set('msg','notpresent',"Nobody seems to be here, guess everybody left${door_action_msg}")
    self.config_parser.set('msg','door_action_msg',", door ${door_status} ${by_whom}")
    self.config_parser.set('msg','status_error_msg',"ERROR Last Operation took too long !!!")
    self.config_parser.add_section('tracker')
    self.config_parser.set('tracker','socket',"/var/run/tuer/presence.socket")        
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
  global sppoo
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

def sendXmppMsg(recipients, msg, resource = "torwaechter", addtimestamp = True, noofflinemsg = False):
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
    sendxmpp_cmd += "--message-type=headline "
  sendxmpp_cmd += recipients
  
  if addtimestamp:
    msg += time.strftime(" (%Y-%m-%d %T)")
  
  popenTimeout2(sendxmpp_cmd, msg)

def distributeXmppMsg(msg,high_priority=False,debug=False):
  if debug == False:
    sendXmppMsg(uwscfg.xmpp_recipients_normal, msg)
    sendXmppMsg(uwscfg.xmpp_recipients_nooffline, msg, noofflinemsg=(not high_priority))
  else:
    sendXmppMsg(uwscfg.xmpp_recipients_debug, "D: " + msg)

def substituteMessageVariables(msg, door_tuple):
  loop_tokens=3
  while loop_tokens > 0 and msg.find("${") > -1:
    #logging.debug("subsMsgVars: loopTok=%d door_tuple=%s msg=%s" % (loop_tokens, str(door_tuple), msg))
    if not door_tuple is None and type(door_tuple[0]) == types.StringType:
      msg = msg.replace('${door_action_msg}', uwscfg.msg_door_action_msg)      
      msg = msg.replace('${door_status}', door_tuple[0]).replace('${by_whom}', "by "+str(door_tuple[1]))
    else:
      msg = msg.replace('${door_action_msg}','').replace('${door_status}','').replace('${by_whom}','')
    loop_tokens-=1
  return msg

def formatAndDistributePresence(presence, door_tuple=(None,None)):
  if presence == "yes":
    distributeXmppMsg(substituteMessageVariables(uwscfg.msg_present, door_tuple))
  else:
    distributeXmppMsg(substituteMessageVariables(uwscfg.msg_notpresent, door_tuple))

def formatAndDistributeWarning(msg, door_tuple=(None,None)):
  distributeXmppMsg("Warning: "+msg , high_priority=True)

current_status = (None, None, None, None) 
def filterAndFormatMessage(new_status):
  global current_status
  if new_status[0] == "error":
    distributeXmppMsg(uwscfg.msg_status_error_msg, high_priority=True)
  elif current_status[0] != new_status[0]:
    distributeXmppMsg("Status: (%s,%s,%s,%s)" % new_status ,debug=True)
  current_status=new_status

def exitHandler(signum, frame):
  global sppoo, conn, sockhandle
  logging.info("Door Status Listener stopping")
  try:
    sppoo.kill()
  except:
    pass
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

logging.info("Update-Xmpp-Status started")
 
if len(sys.argv) > 1:
  uwscfg = UWSConfig(sys.argv[1])
else:
  uwscfg = UWSConfig()

distributeXmppMsg("update-xmpp-status.py started", debug=True)
RE_STATUS = re.compile(r'Status: (\w+), idle')
RE_REQUEST = re.compile(r'Request: (\w+) (?:(Card|Phone) )?(.+)')
RE_PRESENCE = re.compile(r'Presence: (yes|no)(?:, (opened|closed), (.+))?')
RE_BUTTON = re.compile(r'PanicButton|button\d?')
RE_ERROR = re.compile(r'Error: (.+)')
RE_WARNING = re.compile(r'Warning: (.+)')
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
    last_request = (None, None, None)
    not_initial_presence = False
    while True:
      line = conn.readline()
      logging.debug("Got Line: " + line)
      
      uwscfg.checkConfigUpdates()
      
      if line == "":
        raise Exception("EOF on Socket, daemon seems to have quit")      
      
      m = RE_BUTTON.match(line)
      if not m is None:
        distributeXmppMsg(uwscfg.msg_bored)
        continue
        
      m = RE_PRESENCE.match(line)
      if not m is None:
        if not_initial_presence:
          formatAndDistributePresence(m.group(1), m.group(2,3))
        else:
          not_initial_presence=True
          distributeXmppMsg("Initial Presence received: %s" % m.group(1) ,debug=True)
        continue
      
      m = RE_WARNING.match(line)
      if not m is None:
        errorstr = m.group(1)
        logging.error("Recieved Warning: "+errorstr)
        formatAndDistributeWarning(errorstr)
        continue
      
      m = RE_STATUS.match(line)
      if not m is None:
        status = m.group(1)
        filterAndFormatMessage((status,) + last_request)
        last_request = (None, None, None)
        continue
      
      m = RE_REQUEST.match(line)
      if not m is None:  
        last_request = m.group(1,3,2)
        continue
      
      m = RE_ERROR.match(line)
      if not m is None:
        errorstr = m.group(1)
        if "too long!" in errorstr:
          filterAndFormatMessage(("error",) + last_request)
          last_request = (None, None, None)
        else:
          logging.error("Recieved Error: "+errorstr)
          distributeXmppMsg("Error: "+errorstr, debug=True)
          last_request = (None, None, None)
  except Exception, ex:
    logging.error("main: "+str(ex)) 
    traceback.print_exc(file=sys.stdout)
    try:
      sockhandle.close()
    except:
      pass
    conn=None
    sockhandle=None
    time.sleep(5)
