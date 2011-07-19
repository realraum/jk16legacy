#!/bin/bash
TFILE=$(mktemp)
flite -t "$*" $TFILE
ssh -C -i /flash/tuer/id_rsa -o PasswordAuthentication=no -o StrictHostKeyChecking=no root@slug.realraum.at /home/playwav.sh - < $TFILE 
rm $TFILE
