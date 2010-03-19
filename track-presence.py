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
    self.config_parser.set('sensors','remote_cmd',"ssh -i /flash/tuer/id_rsa -o PasswordAuthentication=no %RHOST% %RSHELL% %RSOCKET%")
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

def trackSensorStatusThread(uwscfg,status_tracker,connection_listener):
  #RE_TEMP = re.compile(r'temp\d: (\d+\.\d+)')
  RE_PHOTO = re.compile(r'photo\d: .*(\d+)')
  RE_MOVEMENT = re.compile(r'movement|button\d?|PanicButton')
  RE_ERROR = re.compile(r'Error: (.+)')
  while True:
    uwscfg.checkConfigUpdates()
    try:
      cmd = uwscfg.sensors_remote_cmd.replace("%RHOST%",uwscfg.sensors_remote_host).replace("%RSHELL%",uwscfg.sensors_remote_shell).replace("%RSOCKET%",uwscfg.sensors_remote_socket).split(" ")
      logging.debug("trackSensorStatusThread: Executing: "+" ".join(cmd))
      sshp = subprocess.Popen(cmd, bufsize=1024, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False)
      logging.debug("trackSensorStatusThread: pid %d: running=%d" % (sshp.pid,sshp.poll() is None))
      if not sshp.poll() is None:
        raise Exception("trackSensorStatusThread: subprocess %d not started ?, returncode: %d" % (sshp.pid,sshp.returncode))
      #sshp.stdin.write("listen movement\nlisten button\nlisten sensor\n")
      logging.debug("trackSensorStatusThread: send: listen all")
      sshp.stdin.write("listen all\n")
      sshp.stdin.write("listen movement\n")
      sshp.stdin.write("listen button\n")
      sshp.stdin.write("listen sensor\n")
      while True:
        if not sshp.poll() is None:
          raise Exception("trackSensorStatusThread: subprocess %d finished, returncode: %d" % (sshp.pid,sshp.returncode))
        line = sshp.stdout.readline()
        logging.debug("trackSensorStatusThread:Got Line: " + line)
        if len(line) < 1:
          raise Exception("EOF on Subprocess, daemon seems to have quit, returncode: %d",sshp.returncode)
        connection_listener.distributeData(line)
        m = RE_MOVEMENT.match(line)
        if not m is None:
          status_tracker.movementDetected()
          continue
        m = RE_PHOTO.match(line)
        if not m is None:
          status_tracker.currentLightLevel(m.group(1))
          continue
        m = RE_ERROR.match(line)
        if not m is None:
          logging.error("trackSensorStatusThread: got: "+line) 
    except Exception, ex:
      logging.error("trackSensorStatusThread: "+str(ex)) 
      traceback.print_exc(file=sys.stdout)
      if sshp.poll() is None:
        if sys.hexversion >= 0x020600F0:
          sshp.terminate()
        else:
          subprocess.call(["kill",str(sshp.pid)])
        time.sleep(1.5)
        if sshp.poll() is None:
          logging.error("trackSensorStatusThread: subprocess still alive, sending SIGKILL to pid %d" % (sshp.pid))
          if sys.hexversion >= 0x020600F0:
            sshp.kill()
          else:
            subprocess.call(["kill","-9",str(sshp.pid)])
      time.sleep(5)  
  

def trackDoorStatusThread(uwscfg, status_tracker,connection_listener):
  #socket.setdefaulttimeout(10.0) #affects all new Socket Connections (urllib as well)
  RE_STATUS = re.compile(r'Status: (\w+), idle')
  RE_REQUEST = re.compile(r'Request: (\w+) (?:Card )?(.+)')
  RE_ERROR = re.compile(r'Error: (.+)')
  while True:
    uwscfg.checkConfigUpdates()
    try:
      if not os.path.exists(uwscfg.door_cmd_socket):
        logging.debug("Socketfile '%s' not found, waiting 5 secs" % uwscfg.door_cmd_socket)
        time.sleep(5)
        continue
      sockhandle = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
      sockhandle.connect(uwscfg.door_cmd_socket)
      conn = os.fdopen(sockhandle.fileno())
      sockhandle.send("listen\n")
      sockhandle.send("status\n")
      last_who=None
      while True:
        line = conn.readline()
        logging.debug("trackDoorStatusThread: Got Line: " + line)
        
        if len(line) < 1:
          raise Exception("EOF on Socket, daemon seems to have quit")
        
        connection_listener.distributeData(line)
        
        m = RE_STATUS.match(line)
        if not m is None:
          status = m.group(1)
          if status == "opened":
            status_tracker.doorOpen(last_who)
          if status == "closed":
            status_tracker.doorClosed(last_who)
          last_who = None
          continue
        m = RE_REQUEST.match(line)
        if not m is None:  
          last_who = m.group(2)
          continue
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

############ Status Tracker Class ############

class StatusTracker: #(threading.Thread):
  def __init__(self, uwscfg):
    self.uwscfg=uwscfg
    self.status_change_handler = None
    #State locked by self.lock
    self.door_open=False
    self.door_manual_switch_used=False
    self.last_door_operation_unixts=0
    self.last_movement_unixts=0
    self.last_light_value=0
    self.last_light_unixts=0
    self.lock=threading.Lock()
    #Notify State locked by self.presence_notify_lock
    self.last_somebody_present_result=False
    self.presence_notify_lock=threading.Lock()
    #timer
    self.timer=None
    
  def doorOpen(self,who):
    self.uwscfg.checkConfigUpdates()
    self.lock.acquire()
    self.door_open=True
    self.door_manual_switch_used=(who is None or len(who) == 0)
    self.last_door_operation_unixts=time.time()
    self.lock.release()
    self.checkPresenceStateChangeAndNotify()

  def doorClosed(self,who):
    self.uwscfg.checkConfigUpdates()
    self.lock.acquire()
    self.door_open=False
    self.door_manual_switch_used=(who is None or len(who) == 0)
    self.last_door_operation_unixts=time.time()
    self.lock.release()
    self.checkPresenceStateChangeAndNotify()

  def movementDetected(self):
    self.uwscfg.checkConfigUpdates()
    self.lock.acquire()
    self.last_movement_unixts=time.time()
    self.lock.release()
    self.checkPresenceStateChangeAndNotify()

  def currentLightLevel(self, value):
    self.uwscfg.checkConfigUpdates()
    self.last_light_unixts=time.time()
    self.last_light_value=value;
    self.checkPresenceStateChangeAndNotify()
  
  def checkLight(self, somebody_present=None):
    if somebody_present is None:
      somebody_present=self.somebodyPresent()
    
    if self.last_light_value > self.uwscfg.tracker_photo_flashlight:
      return "Light: flashlight"
    elif self.last_light_value > self.uwscfg.tracker_photo_daylight:
      return "Light: daylight"
    elif self.last_light_value > self.uwscfg.tracker_photo_artif_light:
      if not somebody_present and self.last_light_unixts > self.last_door_operation_unixts:
        return "Light: forgotten"
      else:
        return "Light: on"      
    else:
      return "Light: off"

  
  #TODO: check brightness level from cam or an arduino sensor
  def somebodyPresent(self):
    global uwscfg
    with self.lock:
      if (self.door_open):
        return True
      elif (time.time() - self.last_door_operation_unixts <= self.uwscfg.tracker_sec_wait_movement):
        #start timer, checkPresenceStateChangeAndNotify after tracker_sec_wait_movement
        if not self.timer is None:
          self.timer.cancel()
        self.timer=threading.Timer(self.uwscfg.tracker_sec_wait_movement, self.checkPresenceStateChangeAndNotify)
        self.timer.start()
        return True
      elif (self.last_movement_unixts > self.last_door_operation_unixts and (self.door_manual_switch_used or ( time.time() - self.last_movement_unixts < self.uwscfg.tracker_sec_general_movement_timeout))):
        return True
      else:
        return False
 
  def checkPresenceStateChangeAndNotify(self):
    with self.presence_notify_lock:
      somebody_present = self.somebodyPresent()
      if somebody_present != self.last_somebody_present_result:
        self.last_somebody_present_result = somebody_present
        if not self.status_change_handler is None:
          self.status_change_handler(somebody_present)
 
############ Connection Listener ############
class ConnectionListener:
  def __init__(self, uwscfg, status_tracker):
    self.uwscfg=uwscfg
    self.status_tracker=status_tracker
    self.server_socket=None
    self.running=True
    #register update handler with StatusTracker
    status_tracker.status_change_handler = self.updateStatus
    #Lock protected data:
    self.client_sockets=[]
    self.lock=threading.Lock()
  
  def statusString(self,somebody_present):
    if somebody_present:
      return "Presence: yes" + "\n"
    else:
      return "Presence: no" + "\n"
  
  def updateStatus(self,somebody_present):
    self.distributeData(self.statusString(somebody_present))
    
  def distributeData(self,data):
    with self.lock:
      for socket_to_send_to in self.client_sockets:
        socket_to_send_to.send(data)
    
  def serve(self):
    self.server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        os.remove(self.uwscfg.tracker_server_socket)
    except OSError:
        pass
    self.server_socket.bind(self.uwscfg.tracker_server_socket)
    self.server_socket.listen(2)
    while (self.running):
      (ready_to_read, ready_to_write, in_error) = select.select([self.server_socket]+self.client_sockets, [],  [])
      for socket_to_read in ready_to_read:
        if socket_to_read == self.server_socket:
          newsocketconn, addr = self.server_socket.accept()
          newsocketconn.send(self.statusString(self.status_tracker.somebodyPresent()))
          with self.lock:
            self.client_sockets.append(newsocketconn)
        else:
          #drop all recieved data and watch for closed sockets
          if not socket_to_read.recv(256):
            with self.lock:
              self.client_sockets.remove(socket_to_read)
            try:
              socket_to_read.close()
            except:
              pass
    if self.server_socket:
      self.server_socket.shutdown(socket.SHUT_RDWR)
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

#Status Tracker keeps track of stuff and derives peoples presence from current state
status_tracker = StatusTracker(uwscfg)
#ConnectionListener servers incoming socket connections and distributes status update
connection_listener = ConnectionListener(uwscfg, status_tracker)
#Thread listening for door status changes
track_doorstatus_thread = threading.Thread(target=trackDoorStatusThread,args=(uwscfg,status_tracker,connection_listener),name="trackDoorStatusThread")
track_doorstatus_thread.start()
#Thread listening for movement
track_sensorstatus_thread = threading.Thread(target=trackSensorStatusThread,args=(uwscfg,status_tracker,connection_listener),name="trackSensorStatusThread")
track_sensorstatus_thread.start()

#main routine: serve connections
connection_listener.serve()
