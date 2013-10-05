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
import json
import zmq
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
    self.config_parser.set('powerswitching','secs_movement_before_presence_to_launch_event','1')
    self.config_parser.set('powerswitching','secs_presence_before_movement_to_launch_event','120')
    self.config_parser.set('powerswitching','max_secs_since_movement','600')
    self.config_parser.add_section('slug')
    self.config_parser.set('slug','cgiuri','http://slug.realraum.at/cgi-bin/switch.cgi?id=%ID%&power=%ONOFF%')
    self.config_parser.set('slug','lightleveluri','http://slug.realraum.at/cgi-bin/lightlevel.cgi')
    self.config_parser.set('slug','ids_logo','logo')
    self.config_parser.set('slug','ids_present_day_bright_room','ymhpoweron werkzeug ymhcd')
    self.config_parser.set('slug','ids_present_day_dark_room','ymhpoweron decke werkzeug ymhcd')
    self.config_parser.set('slug','ids_present_night','ymhpoweron werkzeug schreibtisch spots1 labor ymhcd')
    self.config_parser.set('slug','ids_panic','spots1 ymhmute labor werkzeug deckevorne deckehinten')
    self.config_parser.set('slug','ids_decke','deckevorne deckehinten')
    self.config_parser.set('slug','ids_nonpresent_off','ymhvoldown ymhvoldown ymhvoldown ymhvoldown ymhvoldown ymhvoldown ymhvoldown ymhvoldown ymhvoldown ymhvoldown ymhvoldown ymhvoldown lichter ymhpoweroff lichter')
    self.config_parser.set('slug','light_threshold_brightness','400')
    self.config_parser.set('slug','light_difference_decke','100')
    #self.config_parser.set('slug','time_day','6:00-17:00')
    self.config_parser.add_section('debug')
    self.config_parser.set('debug','enabled',"False")
    self.config_parser.add_section('broker')
    self.config_parser.set('broker','uri',"tcp://wuzzler.realraum.at:4244")
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

def getLightValueNow():
  lvalue = touchURL(uwscfg.slug_lightleveluri)
  try:
    return int(lvalue)
  except:
    return None

def haveDaylight():
  dawn_per_month = {1:8, 2:7, 3:6, 4:6, 5:5, 6:5, 7:5, 8:6, 9:7, 10:8, 11:8, 12:8}
  dusk_per_month = {1:15, 2:16, 3:17, 4:19, 5:20, 6:20, 7:20, 8:19, 9:17, 10:17, 11:16, 12:15}
  hour = datetime.datetime.now().hour
  month = datetime.datetime.now().month
  return (hour >= dawn_per_month[month] and hour < dusk_per_month[month])

def isWolfHour():
  hour = datetime.datetime.now().hour
  return (hour >= 2 and hour < 6)

######### ALGOS ###############

def switchLogo(status_presence):
  logo_action=None
  if status_presence:
    logo_action=True
  else:
    if haveDaylight():
      logo_action=False
    else:
       if isWolfHour():
          logo_action=False
       else:
          logo_action=True
  if not logo_action is None:
    logging.info("switchLogo: logo_action:%s" % str(logo_action))
    for id in uwscfg.slug_ids_logo.split(" "):
      switchPower(id,logo_action)

######### EVENTS ###############
unixts_last_movement=0
unixts_last_presence=0
status_presence=None
room_is_bright=None


def eventRoomGotBright():
  global room_is_bright
  logging.debug("eventRoomGotBright()")
  room_is_bright=True

def eventRoomGotDark():
  global room_is_bright
  logging.debug("eventRoomGotDark()")
  room_is_bright=False

def eventMovement():
  global unixts_last_movement, unixts_last_presence
  unixts_last_movement=time.time()
  if (time.time() - unixts_last_presence) <= float(uwscfg.powerswitching_secs_presence_before_movement_to_launch_event):
    eventPresentAndMoved()
    unixts_last_presence=0  # so that eventPresentAndMoved will only launch once per presence event (i.e. supress multiple movement events)


#  global unixts_last_movement
#  if status_presence is True and unixts_last_movement + int(uwscfg.powerswitching_max_secs_since_movement) >= time.time():
#    presumed_state=not (haveDaylight() or isWolfHour())
#    for id in uwscfg.slug_ids_logo.split(" "):
#      switchPower(id,not presumed_state)
#      time.sleep(1);
#      switchPower(id,presumed_state)

def eventPresent():
  global status_presence,room_is_bright,unixts_last_movement,uwscfg,unixts_last_presence
  unixts_last_presence=time.time()
  logging.debug("eventPresent()");
  status_presence=True
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
  switchLogo(status_presence)
  if ( time.time() - unixts_last_movement ) <= float(uwscfg.powerswitching_secs_movement_before_presence_to_launch_event):
    unixts_last_movement=0
    eventPresentAndMoved()

def eventPresentAndMoved():
  global status_presence,room_is_bright
  pass

def eventNobodyHere():
  global status_presence
  logging.debug("eventNobodyHere()");
  status_presence=False
  present_ids=uwscfg.slug_ids_nonpresent_off
  logging.info("event: noone here, switching off: "+present_ids)
  present_id_list=present_ids.split(" ")
  for id in present_id_list:
    time.sleep(0.15)
    switchPower(id,False)
  present_id_list.reverse()
  time.sleep(0.15)
  switchLogo(status_presence)
  time.sleep(2)
  for id in present_id_list:
    time.sleep(0.15)
    switchPower(id,False)

##def eventPanic():
##  logging.info("eventPanic(): switching around: "+uwscfg.slug_ids_panic)
##  lst1 = uwscfg.slug_ids_panic.split(" ")
##  lst2 = map(lambda e:[e,False], lst1)
##  for id in lst1:
##    switchPower(id,False)
##  for delay in map(lambda e: (40-e)/33.0,range(10,33)):
##    e = random.choice(lst2)
##    e[1]=not e[1]
##    switchPower(e[0],e[1])
##    time.sleep(delay)
##  random.shuffle(lst1)
##  for id in lst1:
##    switchPower(id,False)
##  time.sleep(1.2)
##  eventPresent()

def eventPanic():
  global light_value
  logging.info("eventPanic(): switching around: "+uwscfg.slug_ids_panic)
  lst1 = uwscfg.slug_ids_panic.split(" ")
  lst2 = map(lambda e:[e,False], lst1)
  deckenlicht_ids = uwscfg.slug_ids_decke.split(" ")
  ceiling_light_was_on = False
  #guess main light state:
  if len(list(set(deckenlicht_ids) & set(lst1))) > 0:
    light_value_before = light_value
    for id in deckenlicht_ids:
      switchPower(id,False)
    time.sleep(2.8)
    light_value_after = getLightValueNow()
    if not (light_value_before is None or light_value_after is None):
      ceiling_light_was_on = ((light_value_before - light_value_after) > int(uwscfg.slug_light_difference_decke))
    logging.debug("eventPanic: light_value_before: %d, light_value_after: %d, ceiling_light_was_on: %s" % (light_value_before,light_value_after,str(ceiling_light_was_on)))
  for id in lst1:
    switchPower(id,False)
  for times in range(1,6):
    delay = random.choice([0.3,1.4,0.9,0.5,0.3,1.4,0.9,0.5,2.2])
    time.sleep(delay)
    for e in lst2:
      e[1]=not e[1]
      switchPower(e[0],e[1])
  for id in lst1:
    switchPower(id,False)
  time.sleep(1.2)
  eventPresent()
  #we can only test if it was on, we don't any other informatino
  if ceiling_light_was_on:
    for id in deckenlicht_ids:
      switchPower(id,True)


########################

def decodeR3Message(multipart_msg):
    try:
        return (multipart_msg[0], json.loads(multipart_msg[1]))
    except Exception, e:
        logging.debug("decodeR3Message:"+str(e))
        return ("",{})

def exitHandler(signum, frame):
  logging.info("Power Switch Daemon stopping")
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

logging.info("Power Switch Daemon started")

if len(sys.argv) > 1:
  uwscfg = UWSConfig(sys.argv[1])
else:
  uwscfg = UWSConfig()


daylight=None
wolfhour=None
light_value=0
while True:
  try:
    #Start zmq connection to publish / forward sensor data
    zmqctx = zmq.Context()
    zmqctx.linger = 0
    zmqsub = zmqctx.socket(zmq.SUB)
    zmqsub.setsockopt(zmq.SUBSCRIBE, "")
    zmqsub.connect(uwscfg.broker_uri)

    while True:

      data = zmqsub.recv_multipart()
      (structname, dictdata) = decodeR3Message(data)
      logging.debug("Got data: " + structname + ":"+ str(dictdata))

      uwscfg.checkConfigUpdates()

      if structname == "PresenceUpdate" and "Present" in dictdata:
        if dictdata["Present"]:
          eventPresent()
        else:
          eventNobodyHere()
        continue
      elif structname == "BoreDoomButtonPressEvent":
        eventPanic()
        continue
      elif structname == "MovementSensorUpdate" or structname == "DoorAjarUpdate":
        eventMovement()
        continue
      elif structname == "IlluminationSensorUpdate" and "Value" in dictdata:
        light_value = dictdata["Value"]
        light_threshold = int(uwscfg.slug_light_threshold_brightness)
        #logging.debug("photo value: %d  threshold: %s" % (light_value,light_threshold))
        if light_value >= light_threshold:
          eventRoomGotBright()
        else:
          eventRoomGotDark()
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
