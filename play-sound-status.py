#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import os.path
import sys
#import threading
import logging
import logging.handlers
import time
import signal
import subprocess
import types
import ConfigParser
import traceback
import random
import zmq
import zmq.utils.jsonapi as json

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
    #make option variable names case sensitive
    self.config_parser.optionxform = str
    self.config_parser.add_section('cmdlog')
    self.config_parser.set('cmdlog','cmd',"logger %ARG%")
    self.config_parser.set('cmdlog','timeout',"2.0")
    self.config_parser.set('cmdlog','delay',"0.0")
    self.config_parser.set('cmdlog','type',"shellcmd")
    self.config_parser.add_section('slugplayfile')
    self.config_parser.set('slugplayfile','remote_host',"root@slug.realraum.at")
    self.config_parser.set('slugplayfile','remote_shell',"/home/playgst.sh %ARG%")
    self.config_parser.set('slugplayfile','delay',"0.0")
    self.config_parser.set('slugplayfile','type',"remotecmd")
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
    self.config_parser.add_section('nothing')
    self.config_parser.set('nothing','type',"nothing")
    self.config_parser.add_section('randomset1')
    self.config_parser.set('randomset1','type',"random")
    self.config_parser.set('randomset1','one_of',"halflife2 gladosparty")
    self.config_parser.add_section('mapping')
    self.config_parser.set('mapping','DEFAULT',"halflife2")
    self.config_parser.set('mapping','PANIC',"monkeyscream")
    self.config_parser.set('mapping','ERROR',"nothing")
    self.config_parser.set('mapping','stratos',"tardis")
    self.config_parser.set('mapping','xro',"gladosreplaced")
    self.config_parser.set('mapping','equinox',"gladosparty")
    self.config_parser.set('mapping','Rachel',"nothing")
    self.config_parser.add_section('debug')
    self.config_parser.set('debug','enabled',"False")
    self.config_parser.add_section('broker')
    self.config_parser.set('broker','uri',"tcp://torwaechter.realraum.at:4244")    
    self.config_parser.add_section('tracker')
    self.config_parser.set('tracker','secs_movement_before_presence_to_launch_event','1')
    self.config_parser.set('tracker','secs_presence_before_movement_to_launch_event','120')
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
    return self.getSectionValue(name[0:underscore_pos], name[underscore_pos+1:])

  def getSectionValue(self, section, name):
    try:
      return self.config_parser.get(section,name)
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


def runRandomAction(action_list,user,args=[]):
  if not type(action_list) == types.ListType:
    raise ValueError("runRandomAction: action_list must be a list")
  return executeAction(random.choice(action_list),user,args)

def runRemoteCommand(remote_host,remote_shell,user,args=[]):
  global sshp,uwscfg
  sshp = None
  try:
    cmd = "ssh -i /flash/tuer/id_rsa -o PasswordAuthentication=no -o StrictHostKeyChecking=no %RHOST% %RSHELL%"
    cmd = cmd.replace("%RHOST%",remote_host).replace("%RSHELL%",remote_shell).replace("%ARG%", " ".join(args)).replace("%USER%", user)
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
    return False

def runShellCommand(cmd,ptimeout,stdinput,user,args=[]):
  global uwscfg
  cmd = cmd.replace("%ARG%"," ".join(args)).replace("%USER%", user)
  if ptimeout is None or float(ptimeout) > 45:
    ptimeout = 45
  else:
    ptimeout = int(float(ptimeout))
  popenTimeout2(cmd,stdinput,ptimeout=ptimeout)

def executeAction(action_name, user, args=[]):
  if action_name is None:
    logging.error("executeAction: action_name is None")
    return False
  action_type = uwscfg.getValue(action_name+"_type")
  if action_type is None:
    logging.error("executeAction: action %s not found or has no type" % action_name)
    return False
  action_delay=uwscfg.getValue(action_name+"_delay")
  logging.info("executeAction %s of type %s for user %s with delay %s" % (action_name,action_type,user,action_delay))
  if not action_delay is None:
    time.sleep(float(action_delay))

  action_arg = uwscfg.getValue(action_name+"_arg")
  if not action_arg is None:
    args += [action_arg]

  #"registered" actions
  if action_type == "remotecmd":
    return runRemoteCommand(uwscfg.getSectionValue(action_name,"remote_host"), uwscfg.getSectionValue(action_name,"remote_shell"), user=user, args=args)
  elif action_type == "shellcmd":
    return runShellCommand(cmd=uwscfg.getSectionValue(action_name,"cmd"), ptimeout=uwscfg.getSectionValue(action_name,"timeout"), stdinput=uwscfg.getSectionValue(action_name,"stdinput"), user=user, args=args)
  elif action_type == "nothing":
    return True
  elif action_type == "random":
    return runRandomAction(action_list=uwscfg.getSectionValue(action_name,"one_of").split(" "),user=user,args=args)
  else:
    return executeAction(action_type,user=user,args=args)

def playThemeOf(user,fallback_default):
  global uwscfg
  uwscfg.checkConfigUpdates()
  if user is None:
    user = ""
  config=uwscfg.getValue("mapping_"+str(user))
  if config is None:
    config=uwscfg.getValue("mapping_"+str(fallback_default))
  logging.debug("playThemeOf: action for user %s: %s" % (user,config))
  executeAction(config,user,[])

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
        logging.debug("popenTimeout1: subprocess %d finished, returncode: %d" % (sppoo.pid,sppoo.returncode))
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

def decodeR3Message(multipart_msg):
    try:
        return (multipart_msg[0], json.loads(multipart_msg[1]))
    except Exception, e:
        logging.debug("decodeR3Message:"+str(e))
        return ("",{})

def exitHandler(signum, frame):
  logging.info("stopping")
  try:
    zmqsub.close()
    zmqctx.destroy()
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

while True:
  try:
    #Start zmq connection to publish / forward sensor data
    zmqctx = zmq.Context()
    zmqctx.linger = 0
    zmqsub = zmqctx.socket(zmq.SUB)
    zmqsub.setsockopt(zmq.SUBSCRIBE, "DoorCommandEvent")
    zmqsub.setsockopt(zmq.SUBSCRIBE, "PresenceUpdate")
    zmqsub.setsockopt(zmq.SUBSCRIBE, "BoreDoomButtonPressEvent")
#    zmqsub.setsockopt(zmq.SUBSCRIBE, "MovementSensorUpdate")
    zmqsub.setsockopt(zmq.SUBSCRIBE, "DoorAjarUpdate")
    zmqsub.setsockopt(zmq.SUBSCRIBE, "DoorProblemEvent")
    zmqsub.connect(uwscfg.broker_uri)

    last_status=None
    last_user=None
    unixts_panic_button=None
    unixts_last_movement=0
    unixts_last_presence=0
    while True:
      data = zmqsub.recv_multipart()
      (structname, dictdata) = decodeR3Message(data)
      logging.debug("Got data: " + structname + ":"+ str(dictdata))

      #uwscfg.checkConfigUpdates()

      if structname == "PresenceUpdate" and "Present" in dictdata:
        unixts_last_presence=time.time()
        last_status=dictdata["Present"]
        unixts_panic_button=None
        if ( time.time() - unixts_last_movement ) <= float(uwscfg.tracker_secs_movement_before_presence_to_launch_event):
          unixts_last_movement=0
          if last_status:
            playThemeOf(user=last_user, fallback_default="DEFAULT")
        continue
      elif structname == "DoorCommandEvent":
        last_user = dictdata["Who"]
        continue
      elif structname == "BoreDoomButtonPressEvent":
        playThemeOf(user="PANIC", fallback_default="nothing")
        continue
      elif structname == "MovementSensorUpdate" or structname == "DoorAjarUpdate":
        unixts_last_movement=time.time()
        if (time.time() - unixts_last_presence) <= float(uwscfg.tracker_secs_presence_before_movement_to_launch_event):
          unixts_last_presence=0
          if last_status:
            playThemeOf(user=last_user, fallback_default="DEFAULT")
        continue
      elif structname == "DoorProblemEvent" and "Severity" in dictdata:
        playThemeOf(user="ERROR", fallback_default="nothing")
        continue

  except Exception, ex:
    logging.error("main: "+str(ex))
    traceback.print_exc(file=sys.stdout)
    try:
      zmqsub.close()
      zmqctx.destroy()
    except:
      pass
    time.sleep(5)
