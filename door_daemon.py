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
import socket

logging.basicConfig(level=logging.INFO,filename='/var/log/tuer.log',format="%(asctime)s %(message)s",datefmt="%Y-%m-%d %H:%M")

class StatusDisplay():
  def __init__(self):
    self.url_open = 'https://www.realraum.at/cgi/status.cgi?pass=jako16&set=%3Chtml%3E%3Cbody%20bgcolor=%22lime%22%3E%3Ch3%3E%3Ccenter%3ETuer%20ist%20Offen%3C/center%3E%3C/h3%3E%3C/body%3E%3C/html%3E';
    self.url_closed = 'https://www.realraum.at/cgi/status.cgi?pass=jako16&set=%3Chtml%3E%3Cbody%20bgcolor=%22red%22%3E%3Ch3%3E%3Ccenter%3ETuer%20ist%20Geschlossen%3C/center%3E%3C/h3%3E%3C/body%3E%3C/html%3E';
    self.last_status_set=""
    #object.__init__(self)
    
  def display_open(self):
    if self.last_status_set != self.url_open:
      self.last_status_set=self.url_open
      #print "accessing %s\n" % self.last_status_set
      f = urllib.urlopen(self.last_status_set)
      f.read()
      f.close()
    
  def display_closed(self):
    if self.last_status_set != self.url_closed:
      self.last_status_set=self.url_closed
      #print "accessing %s\n" % self.last_status_set
      f = urllib.urlopen(self.last_status_set)
      f.read()
      f.close()


class ArduinoUSBThread ( threading.Thread ):
  def __init__(self, file_dev_ttyusb):
    self.re_isidle = re.compile(r'idle')
    self.re_isopen = re.compile(r'Status: opened, idle')
    self.re_isclosed = re.compile(r'Status: closed, idle')
    self.re_toolong = re.compile(r'took too long!')
    self.min_seconds_between_reset=10;
    self.timestamp_send_reset=0;
    self.running=True
    self.lastline=""
    self.last_status=None
    self.shortsleep = 0
    self.cv_updatestatus = threading.Condition(); #lock ist automatically created withing condition
    self.file_dev_ttyusb=file_dev_ttyusb
    #self.fh = open(self.file_dev_ttyusb,"w+")
    self.fh = os.fdopen(os.open(self.file_dev_ttyusb, os.O_RDWR | os.O_NONBLOCK),"r+") 
    #pythons sucks just like perl: we need nonblock or we can't write to FileHandle while we block reading on same filehandle
    self.statusdisplay = StatusDisplay()
    threading.Thread.__init__(self)
    
  def stop(self):
    self.running=False
    self.fh.close()
    if (self.fh):
      self.fh.close()

  def send_open(self):
    self.send_statusrequest()
    self.cv_updatestatus.acquire()
    if self.re_isidle.search(self.lastline):
      logging.info("Opening Door")
      print("\nSending o..")
      self.fh.write("o");
      print("done\n")
    self.cv_updatestatus.release()
    
  def send_close(self):
    self.send_statusrequest()
    self.cv_updatestatus.acquire()
    if self.re_isidle.search(self.lastline):
      logging.info("Closing Door")
      print("\nSending c..")
      self.fh.write("c");
      print("done\n")
    self.cv_updatestatus.release()
      
  def send_toggle(self):
    self.send_statusrequest()
    self.cv_updatestatus.acquire()
    if self.last_status == "open":
      self.cv_updatestatus.release()
      self.send_close()
    elif self.last_status == "closed":
      self.cv_updatestatus.release()
      self.send_open()
    else:
      self.cv_updatestatus.release()
      
  def send_reset(self):
    self.shortsleep = 20
    logging.info("Resetting Door")    
    #print("\nSending r..")
    self.fh.write("r");
    #print("done\n")

  def send_statusrequest(self):
    self.shortsleep = 20
    #print("\nSending s..")
    self.fh.write("s");
    #print("done\n")
    self.cv_updatestatus.acquire()
    self.cv_updatestatus.wait(5.0)
    self.cv_updatestatus.release()        

  def run (self):
    while (self.running and self.fh):
      try:
        line = self.fh.readline();
      except IOError, e:
        if self.shortsleep > 0:
          time.sleep(0.05)
	  self.shortsleep -= 1
        else:
          time.sleep(0.5)
        continue
      self.cv_updatestatus.acquire()
      self.lastline=line.strip()
      logging.info(self.file_dev_ttyusb+": "+self.lastline)
      if self.re_isclosed.search(self.lastline):
        self.last_status="closed"
        self.statusdisplay.display_closed()
      elif self.re_isopen.search(self.lastline):
        self.last_status="open"
        self.statusdisplay.display_open()
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
    self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        os.remove(self.file_fifo)
    except OSError:
        pass
    self.socket.bind(self.file_fifo)
    self.socket.listen(1)
    while (self.running):
      self.socketconn, addr = self.socket.accept()
      self.conn = os.fdopen(self.socketconn.fileno())
      print "a"
      while 1:
        #~ line=""
        #~ while 1:
          #~ print "d"
          #~ data = self.conn.recv(1024)
          #~ if not data: 
            #~ break
          #~ else:
            #~ line+= data
        line=self.conn.readline()
        if not line:
          break
        print "f"
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
      print "c"
      self.conn.close()
      self.socketconn.close()
    if self.socket:
      self.socket.shutdown(socket.SHUT_RDWR)



fifofile = "/tmp/door_cmd.socket"

arduino = ArduinoUSBThread("/dev/ttyUSB0")
arduino.start()
ctrlfifo = ControlFIFOThread(fifofile,arduino)
ctrlfifo.start()

arduino.send_statusrequest()

def exit_handler(signum, frame):
  global arduino, ctrlfifo
  logging.info("Door Daemon stopping")
  arduino.send_close()
  ctrlfifo.stop()
  arduino.stop()
  sys.exit(0)
  
#signals proapbly don't work because of readline
#signal.signal(signal.SIGTERM, exit_handler)
signal.signal(signal.SIGINT, exit_handler)
signal.signal(signal.SIGQUIT, exit_handler)

logging.info("Door Daemon started")
arduino.join()
ctrlfifo.join()
