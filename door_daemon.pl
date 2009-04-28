#!/usr/bin/perl -w
use IO::Handle;
use IO::Select; 
use Date::Format;
use strict;

my $url_door_open = "https://www.realraum.at/";
my $url_door_closed = "https://www.realraum.at/";

my $door_ttyS = "/dev/ttyUSB0";
my $fifofile = "/tmp/door_cmd.fifo";
unless( -p $fifofile) 
{
  unlink $fifofile;
  system("mkfifo -m 600 $fifofile") && die "Can't mkfifo $fifofile: $!";
  system("setfacl -m u:realraum:rw $fifofile");
  system("setfacl -m u:asterisk:rw $fifofile");
}

my $logfile;
open($logfile,'>>/var/log/tuer.log');
$logfile->autoflush(1);
sub door_log
{
  print $logfile Date::Format::time2str("%Y-%m-%d %T: ",time()).shift()."\n";
}
door_log("Door Daemon started");


$main::door_open=1;
$main::door_closed=0;
$main::tuer_status=$main::door_closed;
#system('wget --no-check-certificate -q -O /dev/null '.$url_door_closed.' &>/dev/null &');


my $fifo=undef;
my $ttyS=undef;
sub handler
{
  #local($sig) = @_;
  door_log("Door Daemon stopped");
  close $logfile;
  close $fifo if (defined $fifo);
  close $ttyS if (defined $ttyS);
  exit(0);
}
$SIG{'INT'} = 'handler';
$SIG{'QUIT'} = 'handler';
$SIG{'KILL'} = 'handler';

while (1)
{
	unless (defined $fifo) { open($fifo,"< $fifofile"); }
	unless (defined $ttyS) { open($ttyS,"< $door_ttyS"); }
	my $read_set = new IO::Select();
	 $read_set->add($fifo); 
	 $read_set->add($ttyS); 
	 
	print $ttyS "s\n";
	 
	do
	{
		my ($rh_set) = IO::Select->select($read_set, undef, undef);
		foreach my $fh (@$rh_set)
		{
			if ($fh == $fifo)
			{
				my $fifo_msg = <$fh>;
				if ($fifo_msg =~ /^(\w+)\s*(.*)/) 
				{
					handle_cmd($1,$2);
				}
			}
			elsif ($fh == $ttyS)
			{
				my $ttyS_msg = <$fh>;
				#last unless ($ttyS_msg);
				print($ttyS_msg);
				door_log($door_ttyS.": ".$ttyS_msg);
				my $tuer=$main::tuer_status;
				$tuer=$main::door_open if $ttyS_msg =~ /open/;
				$tuer=$main::door_closed if $ttyS_msg =~ /close/;
				if ($tuer != $main::tuer_status)
				{
					$main::tuer_status=$tuer;
					if ($tuer == $main::door_open)
					{
						system('wget --no-check-certificate -q -O /dev/null '.$url_door_open.' &>/dev/null &');
					}
					else
					{
						system('wget --no-check-certificate -q -O /dev/null '.$url_door_closed.' &>/dev/null &');
					}
				}
			}
		}
	} until (eof $fifo or eof $ttyS);
	if (eof $fifo) {close($fifo); $fifo=undef;}
	if (eof $ttyS) {close($ttyS); $ttyS=undef;}
}

sub handle_cmd
{
	my $cmd = shift;
	my $who = shift;
	print "c:'$cmd' w:'$who'\n";
	my $tuer=$main::tuer_status;
	if    ($cmd eq "open")   { $tuer=$main::door_open; }
	elsif ($cmd eq "close")  {$tuer=$main::door_closed; }
	elsif ($cmd eq "toggle") {$tuer=!$tuer;}
	elsif ($cmd eq "log") {door_log($who)}
	else {door_log("Invalid Command: $cmd $who")}
	
	if ($tuer != $main::tuer_status)
	{
		if ($tuer == $main::door_open)
		{
			door_log("Door opened by $who");
			print $ttyS "o\n";
			system('wget --no-check-certificate -q -O /dev/null '.$url_door_open.' &>/dev/null &');
		}
		else
		{
			door_log("Door closed by $who");
			print $ttyS "c\n";
			system('wget --no-check-certificate -q -O /dev/null '.$url_door_closed.' &>/dev/null &');
		}
		
	}	
}
