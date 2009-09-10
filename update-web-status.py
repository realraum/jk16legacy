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
import types

#logging.basicConfig(level=logging.INFO,filename='/var/log/tmp/tuer.log',format="%(asctime)s %(message)s",datefmt="%Y-%m-%d %H:%M")
logging.basicConfig(
  level=logging.ERROR,
  format="%(asctime)s %(message)s",
  datefmt="%Y-%m-%d %H:%M"
  )

URL_OPEN = 'https://www.realraum.at/cgi/status.cgi?pass=jako16&set=%3Chtml%3E%3Cbody%20bgcolor=%22lime%22%3E%3Ccenter%3E%3Cb%3ET%26uuml%3Br%20ist%20Offen%3C/b%3E%3C/center%3E%3C/body%3E%3C/html%3E'
URL_CLOSED = 'https://www.realraum.at/cgi/status.cgi?pass=jako16&set=%3Chtml%3E%3Cbody%20bgcolor=%22red%22%3E%3Cb%3E%3Ccenter%3ET%26uuml%3Br%20ist%20Geschlossen%3C/center%3E%3C/b%3E%3C/body%3E%3C/html%3E'
SENDXMPP_RECIPIENTS_DEBUG = 'xro@jabber.tittelbach.at'
SENDXMPP_RECIPIENTS_NORMAL = ['xro@jabber.tittelbach.at', 'otti@wirdorange.org']
SENDXMPP_RECIPIENTS_NOOFFLINE = 'the-equinox@jabber.org'
SENDXMPP_MSG_OPENED = "Realraum Tür wurde%s geöffnet"
SENDXMPP_MSG_CLOSED = "Realraum Tür wurde%s geschlossen"
sendxmpp_msg_lastmsg = ""
action_by = ""
sendxmpp_firstmsg = True

def sendXmppMsg(recipients, msg, resource = "torwaechter", addtimestamp = True, noofflinemsg = False):
  if type(recipients) == types.ListType:
    recipients = " ".join(recipients)
  if type(recipients) == types.UnicodeType:
    recipients = recipients.decode("utf-8")
  if type(recipients) != types.StringType:
    raise Exception("list of recipients in unknown format, can't send message")
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
    sppoo.wait()
  except Exception, e:
    logging.error(str(e))
  logging.debug("XMPPmessage sent: '%s'"  % msg)
  
def distributeXmppMsg(msg):
  global sendxmpp_firstmsg, sendxmpp_msg_lastmsg
  if sendxmpp_firstmsg:
    sendxmpp_msg_lastmsg = msg
    sendxmpp_firstmsg = False
  if msg != sendxmpp_msg_lastmsg:    
    sendXmppMsg(SENDXMPP_RECIPIENTS_NORMAL, msg)
    sendXmppMsg(SENDXMPP_RECIPIENTS_NOOFFLINE, msg, noofflinemsg=True)
  else:
    sendXmppMsg(SENDXMPP_RECIPIENTS_DEBUG, "D: " + msg)
  sendxmpp_msg_lastmsg = msg
  
def touchURL(url):
  try:
    f = urllib.urlopen(url)
    f.read()
    f.close()
  except Exception, e:
    logging.error(str(e))
  
def displayOpen():
  touchURL(URL_OPEN)
  distributeXmppMsg(SENDXMPP_MSG_OPENED % action_by)
  
def displayClosed():
  touchURL(URL_CLOSED)
  distributeXmppMsg(SENDXMPP_MSG_CLOSED % action_by)
  
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
  SENDXMPP_RECIPIENTS_NORMAL = sys.argv[2:]

sendXmppMsg(SENDXMPP_RECIPIENTS_DEBUG,"D: update-web-status.py started")

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
      logging.info("Got Line: " + line)
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
          distributeXmppMsg(SENDXMPP_RECIPIENTS_DEBUG, "Door Error: "+errorstr)
        else:
          sendXmppMsg(SENDXMPP_RECIPIENTS_DEBUG, "D: Error: "+errorstr)
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

