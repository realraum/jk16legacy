#!/bin/bash
TFILE=$(mktemp)
flite -t "$*" $TFILE
toolame $TFILE - 2>/dev/null | ssh -o PasswordAuthentication=no -o StrictHostKeyChecking=no root@slug.realraum.at /home/playmp3.sh -
rm $TFILE
