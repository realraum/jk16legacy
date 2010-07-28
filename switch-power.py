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
import datetime
import random
import traceback

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
    self.config_parser.add_section('powerswitching')
    self.config_parser.set('powerswitching','min_secs_periodical_event','59')
    self.config_parser.set('powerswitching','max_secs_since_movement','600')
    self.config_parser.add_section('slug')
    self.config_parser.set('slug','cgiuri','http://slug.realraum.at/cgi-bin/switch.cgi?id=%ID%&power=%ONOFF%')
    self.config_parser.set('slug','ids_logo','logo')
    self.config_parser.set('slug','ids_present_day_bright_room','ymhpoweron werkzeug ymhcd')
    self.config_parser.set('slug','ids_present_day_dark_room','ymhpoweron decke werkzeug ymhcd')
    self.config_parser.set('slug','ids_present_night','ymhpoweron werkzeug schreibtisch idee labor ymhcd')
    self.config_parser.set('slug','ids_panic','idee ymhmute labor werkzeug deckevorne deckehinten')
    self.config_parser.set('slug','ids_nonpresent_off','ymhvoldown ymhvoldown ymhvoldown ymhvoldown ymhvoldown ymhvoldown ymhvoldown ymhvoldown ymhvoldown ymhvoldown ymhvoldown ymhvoldown lichter ymhpoweroff lichter')
    self.config_parser.set('slug','light_threshold_brightness','400')
    #self.config_parser.set('slug','time_day','6:00-17:00')
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

def haveDaylight():
  dawn_per_month = {1:8, 2:7, 3:6, 4:6, 5:5, 6:5, 7:5, 8:6, 9:7, 10:8, 11:8, 12:8}
  dusk_per_month = {1:16, 2:17, 3:18, 4:20, 5:20, 6:21, 7:21, 8:20, 9:19, 10:18, 11:16, 12:16}
  hour = datetime.datetime.now().hour
  month = datetime.datetime.now().month
  return (hour >= dawn_per_month[month] and hour < dusk_per_month[month])

def isWolfHour():
  hour = datetime.datetime.now().hour
  return (hour >= 2 and hour < 6)

######### EVENTS ###############  
unixts_last_movement=0
status_presense=None
room_is_bright=None

def eventRoomGotBright():
  global room_is_bright
  logging.debug("eventRoomGotBright()")
  room_is_bright=True

def eventRoomGotDark():
  global room_is_bright
  logging.debug("eventRoomGotDark()")
  room_is_bright=False

def eventDaylightStart():
  logging.debug("eventDaylightStart()")
  for id in uwscfg.slug_ids_logo.split(" "):
    switchPower(id,False)

def eventDaylightStop():
  logging.debug("eventDaylightStop()")
  if not isWolfHour():
    for id in uwscfg.slug_ids_logo.split(" "):
      switchPower(id,True)

def eventWolfHourStart():
  logging.debug("eventWolfHourStart()")
  for id in uwscfg.slug_ids_logo.split(" "):
    switchPower(id,False)

def eventWolfHourStop():
  logging.debug("eventWolfHourStop()")
  if haveDaylight():
    for id in uwscfg.slug_ids_logo.split(" "):
      switchPower(id,True)

def eventMovement():
  global unixts_last_movement
  unixts_last_movement=time.time()

def eventPeriodical():
  pass

#  global unixts_last_movement
#  if status_presense is True and unixts_last_movement + int(uwscfg.powerswitching_max_secs_since_movement) >= time.time():
#    presumed_state=not (haveDaylight() or isWolfHour())
#    logging.debug("event: periodical event")
#    for id in uwscfg.slug_ids_logo.split(" "):
#      switchPower(id,not presumed_state)
#      time.sleep(1);
#      switchPower(id,presumed_state)

def eventPresent():
  global status_presense,room_is_bright
  logging.debug("eventPresent()");
  status_presense=True
  if haveDaylight():
    if room_is_bright is False:
      present_ids=uwscfg.slug_ids_present_day_dark_room
    else:
      present_ids=uwscfg.slug_ids_present_day_bright_room
  else:
    present_ids=uwscfg.slug_ids_present_night
  logging.info("event: someone present, switching on: "+present_ids)
  for id in present_ids.split(" "):
    switchPower(id,True)

def eventNobodyHere():
  global status_presense
  logging.debug("eventNobodyHere()");
  status_presense=False
  present_ids=uwscfg.slug_ids_nonpresent_off
  logging.info("event: noone here, switching off: "+present_ids)
  for id in present_ids.split(" "):
    time.sleep(0.2)
    switchPower(id,False)

def eventPanic():
  logging.info("eventPanic(): switching around: "+uwscfg.slug_ids_panic)
  lst1 = uwscfg.slug_ids_panic.split(" ")
  lst2 = map(lambda e:[e,True], lst1)
  for id in lst1:
    switchPower(id,True)
  for delay in map(lambda e: (40-e)/33.0,range(0,20)):
    e = random.choice(lst2)
    e[1]=not e[1]
    switchPower(e[0],e[1]) 
    time.sleep(delay)
  random.shuffle(lst1)
  for id in lst1:
    switchPower(id,False)
  time.sleep(1.2)
  eventPresent()
    

########################

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
RE_PRESENCE = re.compile(r'Presence: (yes|no)(?:, (opened|closed), (.+))?')
RE_BUTTON = re.compile(r'PanicButton|button\d?')
RE_MOVEMENT = re.compile(r'movement')
RE_PHOTO = re.compile(r'photo\d: [^0-9]*?(\d+)')
daylight=None
wolfhour=None
unixts_last_periodical=0
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

      if haveDaylight() != daylight:
        daylight = haveDaylight()
        if daylight:
          eventDaylightStart()
        else:
          eventDaylightStop()

      if isWolfHour() != wolfhour:
        wolfhour = isWolfHour()
        if wolfhour:
          eventWolfHourStart()
        else:
          eventWolfHourStop()
     
      if unixts_last_periodical + int(uwscfg.powerswitching_min_secs_periodical_event) <= time.time():
        unixts_last_periodical = time.time()
        eventPeriodical()

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
      m = RE_MOVEMENT.match(line)
      if not m is None:
        eventMovement()
        continue
      m = RE_PHOTO.match(line)
      if not m is None:
        if m.group(1) >= int(uwscfg.slug_light_threshold_brightness):
          eventRoomGotBright()
        else:
          eventRoomGotDark()
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
