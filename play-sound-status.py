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
    self.config_parser.add_section('cmdlog')
    self.config_parser.set('cmdlog','cmd',"logger %ARG%")
    self.config_parser.set('cmdlog','timeout',"2.0")
    self.config_parser.set('cmdlog','delay',"0.0")
    self.config_parser.set('cmdlog','type',"shellcmd")
    self.config_parser.add_section('slugplaymp3')
    self.config_parser.set('slugplaymp3','remote_host',"root@slug.realraum.at")
    self.config_parser.set('slugplaymp3','remote_shell',"/home/playmp3.sh %ARG%")
    self.config_parser.set('slugplaymp3','delay',"0.0")
    self.config_parser.set('slugplaymp3','type',"remotecmd")
    self.config_parser.add_section('halflife2')
    self.config_parser.set('halflife2','arg',"/home/half-life-door.mp3")
    self.config_parser.set('halflife2','type',"slugplaymp3")
    self.config_parser.set('halflife2','delay',"0.2")    
    self.config_parser.add_section('tardis')
    self.config_parser.set('tardis','arg',"/home/tardis.mp3")
    self.config_parser.set('tardis','type',"slugplaymp3")
    self.config_parser.add_section('sg1aliengreeting')
    self.config_parser.set('sg1aliengreeting','arg',"/home/sg1aliengreeting.mp3")
    self.config_parser.set('sg1aliengreeting','type',"slugplaymp3")
    self.config_parser.add_section('monkeyscream')
    self.config_parser.set('monkeyscream','arg',"/home/monkeyscream.mp3")
    self.config_parser.set('monkeyscream','delay',"1.5")
    self.config_parser.set('monkeyscream','type',"slugplaymp3")
    self.config_parser.add_section('gladosparty')
    self.config_parser.set('gladosparty','arg',"/home/glados_party.mp3")
    self.config_parser.set('gladosparty','type',"slugplaymp3")
    self.config_parser.add_section('gladosbaked')
    self.config_parser.set('gladosbaked','arg',"/home/glados_baked.mp3")
    self.config_parser.set('gladosbaked','type',"slugplaymp3")
    self.config_parser.add_section('gladoswelcome')
    self.config_parser.set('gladoswelcome','arg',"/home/glados_welcome.mp3")
    self.config_parser.set('gladoswelcome','type',"slugplaymp3")
    self.config_parser.add_section('gladosreplaced')
    self.config_parser.set('gladosreplaced','arg',"/home/glados_replaced_with_life_fire.mp3")
    self.config_parser.set('gladosreplaced','type',"slugplaymp3")
    self.config_parser.add_section('mapping')
    self.config_parser.set('mapping','default',"halflife2")
    self.config_parser.set('mapping','panic',"monkeyscream")
    self.config_parser.set('mapping','stratos',"tardis")
    self.config_parser.set('mapping','xro',"gladosreplaced")
    self.config_parser.set('mapping','equinox',"gladosparty")
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

  def getValue(self, name):
    underscore_pos=name.find('_')
    if underscore_pos < 0:
      raise AttributeError
    try:
      return self.config_parser.get(name[0:underscore_pos], name[underscore_pos+1:])
    except (ConfigParser.NoOptionError, ConfigParser.NoSectionError):
      return None

  def __getattr__(self, name):
    underscore_pos=name.find('_')
    if underscore_pos < 0:
      raise AttributeError
    try:
      return self.config_parser.get(name[0:underscore_pos], name[underscore_pos+1:])
    except (ConfigParser.NoOptionError, ConfigParser.NoSectionError):
      raise AttributeError



def runRemoteCommand(remote_host,remote_shell,args=[]):
  global sshp,uwscfg
  sshp = None
  try:
    cmd = "ssh -i /flash/tuer/id_rsa -o PasswordAuthentication=no -o StrictHostKeyChecking=no %RHOST% %RSHELL%"
    cmd = cmd.replace("%RHOST%",remote_host).replace("%RSHELL%",remote_shell).replace("%ARG%", " ".join(args))
    logging.debug("runRemoteCommand: Executing: "+cmd)
    sshp = subprocess.Popen(cmd.split(" "), bufsize=1024, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False)
    logging.debug("runRemoteCommand: pid %d: running=%d" % (sshp.pid,sshp.poll() is None))
    if not sshp.poll() is None:
      logging.error("runRemoteCommand: subprocess %d not started ?, returncode: %d" % (sshp.pid,sshp.returncode))
      return False
    return True
  except Exception, ex:
    logging.error("runRemoteCommand: "+str(ex)) 
    traceback.print_exc(file=sys.stdout)
    if not sshp is None and sshp.poll() is None:
      if sys.hexversion >= 0x020600F0:
        sshp.terminate()
      else:
        subprocess.call(["kill",str(sshp.pid)])
      time.sleep(1.5)
      if sshp.poll() is None:
        logging.error("runRemoteCommand: subprocess still alive, sending SIGKILL to pid %d" % (sshp.pid))
        if sys.hexversion >= 0x020600F0:
          sshp.kill()
        else:
          subprocess.call(["kill","-9",str(sshp.pid)])
    time.sleep(5)

def runShellCommand(cmd,ptimeout,stdinput,args=[]):
  global uwscfg
  cmd = cmd.replace("%ARG%"," ".join(args))
  if ptimeout is None or float(ptimeout) > 45:
    ptimeout = 45
  popenTimeout2(cmd,stdinput,float(ptimeout))

def executeAction(action_name, args=[]):
  if action_name is None:
    logging.error("executeAction: action_name is None")
    return False
  action_type = uwscfg.getValue(action_name+"_type") 
  if action_type is None:
    logging.error("executeAction: action %s not found or has no type" % action_name)
    return False
  action_delay=uwscfg.getValue(action_name+"_delay")
  logging.debug("executeAction, action_name=%s, action_type=%s, action_delay=%s" % (action_name,action_type,action_delay))  
  if not action_delay is None:
    time.sleep(float(action_delay))
  
  action_arg = uwscfg.getValue(action_name+"_arg")
  if not action_arg is None:
    args += [action_arg]
  
  #"registered" actions
  if action_type == "remotecmd":
    return runRemoteCommand(uwscfg.getValue(action_name+"_remote_host"), uwscfg.getValue(action_name+"_remote_shell"), args)
  elif action_type == "shellcmd":
    return runShellCommand(cmd=uwscfg.getValue(action_name+"_cmd"), ptimeout=uwscfg.getValue(action_name+"_timeout"), stdinput=uwscfg.getValue(action_name+"_stdinput"), args=args)
  else:
    return executeAction(action_type,args)
  
def playThemeOf(user):
  global uwscfg
  uwscfg.checkConfigUpdates()
  config=uwscfg.getValue("mapping_"+str(user))
  if config is None:
    config=uwscfg.getValue("mapping_default")
  logging.debug("playThemeOf: action for user %s: %s" % (user,config))
  executeAction(config)

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
    if not pinput is None:
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
RE_REQUEST = re.compile(r'Request: (\w+) (?:(Card|Phone) )?(.+)')
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
      
      #uwscfg.checkConfigUpdates()
      
      if line == "":
        raise Exception("EOF on Socket, daemon seems to have quit")
      
      m = RE_PRESENCE.match(line)
      if not m is None:
        status = m.group(1)
        last_status=(status == "yes")
        unixts_panic_button=None
        if last_status:
          playThemeOf(user=m.group(3))
        continue
        
      m = RE_BUTTON.match(line)
      if not m is None:
        playThemeOf(user="panic")
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
