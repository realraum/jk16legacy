#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import sys
import threading
import logging
import urllib
import time
import signal
import re

logging.basicConfig(level=logging.INFO,filename='/var/log/tuer.log')

class StatusDisplay(object):
   def __init__(self):
    self.url_open = 'https://www.realraum.at/cgi/status.cgi?pass=jako16&set=%3Chtml%3E%3Cbody%20bgcolor=%22lime%22%3E%3Ch3%3E%3Ccenter%3ETuer%20ist%20Offen%3C/center%3E%3C/h3%3E%3C/body%3E%3C/html%3E';
    self.url_closed = 'https://www.realraum.at/cgi/status.cgi?pass=jako16&set=%3Chtml%3E%3Cbody%20bgcolor=%22red%22%3E%3Ch3%3E%3Ccenter%3ETuer%20ist%20Geschlossen%3C/center%3E%3C/h3%3E%3C/body%3E%3C/html%3E';
    self.last_status_set=self.url_open
    #object.__init__(self)
    
    def display_open(self):
      if self.last_status_set != self.url_open:
        self.last_status_set=self.url_open
        f = urllib.urlopen(self.last_status_set)
        f.close()
      
    def display_closed(self):
      if self.last_status_set != self.url_closed:
        self.last_status_set=self.url_closed
        f = urllib.urlopen(self.last_status_set)
        f.close()


class ArduinoUSBThread ( threading.Thread ):
  def __init__(self, file_dev_ttyusb):
    self.re_isidle = re.compile(r'open')
    self.re_isopen = re.compile(r'open')
    self.re_isclosed = re.compile(r'close|closing')
    self.re_toolong = re.compile(r'took too long!')
    self.min_seconds_between_reset=10;
    self.timestamp_send_reset=0;
    self.running=True
    self.lastline=""
    self.last_status=None
    self.cv_updatestatus = threading.Condition(); #lock ist automatically created withing condition
    self.file_dev_ttyusb=file_dev_ttyusb
    self.statusdisplay = StatusDisplay()
    threading.Thread.__init__(self)
    
  def stop(self):
    self.running=False
    self.fh.close()

  def send_open(self):
    self.send_statusrequest()
    self.cv_updatestatus.acquire()
    self.cv_updatestatus.wait(3.0)
    self.cv_updatestatus.release()
    if re_isidle.search(self.lastline):
      logging.info("Opening Door")
      self.fh.write("o");
    
  def send_close(self):
    self.send_statusrequest()
    self.cv_updatestatus.acquire()
    self.cv_updatestatus.wait(3.0)
    self.cv_updatestatus.release()    
    if re_isidle.search(self.lastline):
      logging.info("Closing Door")
      self.fh.write("c");
      
  def send_toggle(self):
    self.send_statusrequest()
    self.cv_updatestatus.acquire()
    self.cv_updatestatus.wait(3.0)
    self.cv_updatestatus.release()
    if re_isidle.search(self.lastline):
      if self.last_status == "open":
        logging.info("Closing Door")
        self.fh.write("c");
      elif self.last_status == "closed":
        logging.info("Opening Door")
        self.fh.write("o");
      
  def send_reset(self):
    logging.info("Resetting Door")
    self.fh.write("r");

  def send_statusrequest(self):
    self.fh.write("s");

  def run (self):
    self.fh = open(self.file_dev_ttyusb,"rw")
    while (self.running):
      print "."
      line = self.fh.readline();
      self.cv_updatestatus.acquire()
      self.lastline=line
      logging.info(self.file_dev_ttyusb+": "+self.lastline)
      if self.re_isclosed.search(self.lastline):
        self.last_status="closed"
        self.statusdisplay.display_open()
      elif self.re_isopen.search(self.lastline):
        self.last_status="open"
        self.statusdisplay.display_closed()
      elif self.re_toolong.search(self.lastline):
        self.last_status="error"
        if (time.time() - self.timestamp_send_reset) > self.min_seconds_between_reset:
          self.timestamp_send_reset=time.time()
          self.send_reset()
      self.cv_updatestatus.notifyAll()
      self.cv_updatestatus.release()
    if self.fh:
      self.fh.close()

class ControlFIFOThread ( threading.Thread ):
  def __init__(self, file_fifo, arduino):
    self.running=True
    self.file_fifo=file_fifo
    self.arduino = arduino
    self.re_cmd = re.compile(r'^(\w+)\s*(.*)')
    threading.Thread.__init__(self)
  
  def stop(self):
    self.running=False
    self.fh.close()
  
  def run (self):
    self.fh = open(self.file_fifo,"r")
    while (self.running):
      print "."
      line=self.fh.readline()
      m = self.re_cmd.match(line)
      if not m is None:
        (cmd,who) = m.group(1,2)
        if cmd == "open":
          logging.info("Open Requested by %s" % who)
          arduino.send_open()
        elif cmd == "close":
          logging.info("Close Requested by %s" % who)
          arduino.send_close()
        elif cmd == "toggle":
          logging.info("Toggle Requested by %s" % who)
          arduino.send_toggle()
        elif cmd == "reset":
          logging.info("Reset Requested by %s" % who)
          arduino.send_reset()
        elif cmd == "status":
          arduino.send_statusrequest()
        elif cmd == "log":
          logging.info(who)
        else:
          logging.info("Invalid Command %s %s" % (cmd,who))
    if self.fh:
      self.fh.close()



fifofile = "/tmp/door_cmd.fifo"

if (not os.path.exists(fifofile)):
  os.system("mkfifo -m 600 $fifofile")
  os.system("setfacl -m u:realraum:rw $fifofile")
  os.system("setfacl -m u:asterisk:rw $fifofile")

logging.info("Door Daemon started")

arduino = ArduinoUSBThread("/dev/ttyUSB0")
arduino.start()
ctrlfifo = ControlFIFOThread(fifofile,arduino)
ctrlfifo.start()

def exit_handler(signum, frame):
  global arduino, ctrlfifo
  logging.info("Door Daemon stopping")
  arduino.send_close()
  ctrlfifo.stop()
  arduino.stop()
  sys.exit(0)
  
signal.signal(signal.SIGTERM, exit_handler)
signal.signal(signal.SIGINT, exit_handler)
signal.signal(signal.SIGQUIT, exit_handler)
