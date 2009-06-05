#!/bin/sh

URL_OPENED='https://www.realraum.at/cgi/status.cgi?pass=jako16&set=%3Chtml%3E%3Cbody%20bgcolor=%22lime%22%3E%3Ccenter%3E%3Cb%3ET%26uuml%3Br%20ist%20Offen%3C/b%3E%3C/center%3E%3C/body%3E%3C/html%3E'
URL_CLOSED='https://www.realraum.at/cgi/status.cgi?pass=jako16&set=%3Chtml%3E%3Cbody%20bgcolor=%22red%22%3E%3Cb%3E%3Ccenter%3ET%26uuml%3Br%20ist%20Geschlossen%3C/center%3E%3C/b%3E%3C/body%3E%3C/html%3E'

if [ -z "$1" ]; then
  echo "Usage: update-web-status.sh (open|close)"
  exit 1
fi

case "$1" in
  open)
    wget --no-check-certificate -O /dev/null $URL_OPENED > /dev/null 2>&1
    ;;
  close)
    wget --no-check-certificate -O /dev/null $URL_CLOSED > /dev/null 2>&1
    ;;
  *)
    echo "Invalid argument '$1' != (open|close)"
    exit 1;
    ;;
esac

if [ $? -ne 0 ]; then
  echo "Error"
  exit 2
fi

echo "Ok"
exit 0
