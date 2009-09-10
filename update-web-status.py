#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import sys
#import threading
import logging
import urllib
import time
import signal
import re
import socket
import subprocess

#logging.basicConfig(level=logging.INFO,filename='/var/log/tmp/tuer.log',format="%(asctime)s %(message)s",datefmt="%Y-%m-%d %H:%M")
logging.basicConfig(level=logging.ERROR,format="%(asctime)s %(message)s",datefmt="%Y-%m-%d %H:%M")

url_open = 'https://www.realraum.at/cgi/status.cgi?pass=jako16&set=%3Chtml%3E%3Cbody%20bgcolor=%22lime%22%3E%3Ccenter%3E%3Cb%3ET%26uuml%3Br%20ist%20Offen%3C/b%3E%3C/center%3E%3C/body%3E%3C/html%3E'
url_closed = 'https://www.realraum.at/cgi/status.cgi?pass=jako16&set=%3Chtml%3E%3Cbody%20bgcolor=%22red%22%3E%3Cb%3E%3Ccenter%3ET%26uuml%3Br%20ist%20Geschlossen%3C/center%3E%3C/b%3E%3C/body%3E%3C/html%3E'
sendxmpp_recipients = 'xro@jabber.tittelbach.at otti@wirdorange.org'
sendxmpp_cmd = 'sendxmpp -u realrauminfo -p 5SPjTdub -j jabber.tittelbach.at -r torwaechter -t '
sendxmpp_msg_opened="Realraum Tür wurde%s geöffnet"
sendxmpp_msg_closed="Realraum Tür wurde%s geschlossen"
action_by=""

def display_open():
  try:
    #print "accessing %s\n" % self.last_status_set
    f = urllib.urlopen(url_open)
    f.read()
    f.close()
  except:
    pass
  try:
    logging.debug("Starting " + sendxmpp_cmd+sendxmpp_recipients)
    sppoo = subprocess.Popen(sendxmpp_cmd+sendxmpp_recipients,stdin=subprocess.PIPE,shell=True)
    sppoo.communicate(input=(sendxmpp_msg_opened % action_by)+time.strftime(" (%Y-%m-%d %T)"))
    sppoo.wait()
    logging.debug("XMPP Message about door opening sent")
  except:
    pass

def display_closed():
  try:
    #print "accessing %s\n" % self.last_status_set
    f = urllib.urlopen(url_closed)
    f.read()
    f.close()
  except Exception, e:
    logging.error(str(e))
    pass
  try:
    logging.debug("Starting " + sendxmpp_cmd+sendxmpp_recipients)
    sppoo = subprocess.Popen(sendxmpp_cmd+sendxmpp_recipients,stdin=subprocess.PIPE,shell=True)
    sppoo.communicate(input=(sendxmpp_msg_closed % action_by)+time.strftime(" (%Y-%m-%d %T)"))
    sppoo.wait()
    logging.debug("XMPP Message about door closing sent")
  except Exception, e:
    logging.error(str(e))
    pass

def exit_handler(signum, frame):
  logging.info("Door Status Listener stopping")
  try:
    conn.close()
  except Exception, e:
    logging.error(str(e))
    pass
  try:
    sockhandle.close()
  except Exception, e:
    logging.error(str(e))
    pass
  sys.exit(0)
  
#signals proapbly don't work because of readline
#signal.signal(signal.SIGTERM, exit_handler)
signal.signal(signal.SIGINT, exit_handler)
signal.signal(signal.SIGQUIT, exit_handler)

logging.info("Door Status Listener started")

if len(sys.argv) > 1:
  socketfile=sys.argv[1]
else:
  socketfile = "/var/run/tuer/door_cmd.socket"
if len(sys.argv) > 2:
  sendxmpp_recipients = " ".join(sys.argv[2:])
sockhandle=socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
re_status = re.compile(r'Status: (\w+), idle')
re_request = re.compile(r'Request: (\w+) (?:Card )?(.+)')
while True:
  try:
    sockhandle.connect(socketfile)
    conn = os.fdopen(sockhandle.fileno())
    sockhandle.send("listen\n")
    sockhandle.send("status\n")
    while True:
      line = conn.readline()
      logging.info("Got Line: "+line)
      m = re_status.match(line)
      if not m is None:
        status = m.group(1)
        if status == "opened":
          display_open()
        if status == "closed":
          display_closed()
      m = re_request.match(line)
      if not m is None:  
        #(rq_action,rq_by) = m.group(1,2)
        action_by=" von "+m.group(2)
      else:
        action_by=""
  except Exception, e:
    logging.error(str(e)) 
    try:
      conn.close()
    except:
      pass
    try:
      sockhandle.close()
    except:
      pass
    time.sleep(5)

