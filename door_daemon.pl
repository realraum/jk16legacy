#!/usr/bin/perl -w
use POSIX qw();
use IO::Handle;
use IO::Select; 
use Date::Format;
use Fcntl; 
use strict;

my $url_door_open = "https://www.realraum.at/";
my $url_door_closed = "https://www.realraum.at/";

my $door_ttyusb_dev = "/dev/ttyUSB0";
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
my $ttyusb=undef;
sub handler
{
  #local($sig) = @_;
  door_log("Door Daemon stopped");
  close $logfile;
  close $fifo if (defined $fifo);
  close $ttyusb if (defined $ttyusb);
  exit(0);
}
$SIG{'INT'} = 'handler';
$SIG{'QUIT'} = 'handler';
$SIG{'KILL'} = 'handler';

while (1)
{
	unless (defined $ttyusb) {
		print "open usb\n";
		sysopen($ttyusb, $door_ttyusb_dev, O_RDWR | O_NONBLOCK); 
		$ttyusb->autoflush(1);
		my $termios = POSIX::Termios->new;
		$termios->getattr(fileno $ttyusb);
		$termios->setispeed( &POSIX::B9600 );
		$termios->setospeed( &POSIX::B9600 );
		#$termios->setcflag( $termios->getcflag & ~(&POSIX::PARENB | &POSIX::PARODD) & (~&POSIX::CSIZE | &POSIX::CS8));
		$termios->setattr(fileno $ttyusb);
		print "x\n";
	}
	unless (defined $fifo) {print "open fifo\n"; sysopen($fifo,$fifofile, O_RDONLY | O_NONBLOCK); print "x\n";}
	my $read_set = new IO::Select();
	 $read_set->add($fifo); 
	 $read_set->add($ttyusb); 
	print $ttyusb "s";
	 
	do
	{
		print $main::tuer_status,"\n";
		my ($rh_set) = IO::Select->select($read_set, undef, undef);
		foreach my $fh (@$rh_set)
		{
			if ($fh == $fifo)
			{
				my $fifo_msg = <$fh>;
				last unless ($fifo_msg);
				if ($fifo_msg =~ /^(\w+)\s*(.*)/) 
				{
					handle_cmd($1,$2);
				}
			}
			elsif ($fh == $ttyusb)
			{
				my $ttyusb_msg = <$fh>;
				last unless ($ttyusb_msg);
				print($ttyusb_msg);
				door_log($door_ttyusb_dev.": ".$ttyusb_msg);
				my $tuer=$main::tuer_status;
				$tuer=$main::door_open if $ttyusb_msg =~ /open/;
				$tuer=$main::door_closed if $ttyusb_msg =~ /close/;
				if (not $tuer == $main::tuer_status)
				{
					$main::tuer_status=$tuer;
					if ($tuer == $main::door_open)
					{
						print "change to open\n";
						system('wget --no-check-certificate -q -O /dev/null '.$url_door_open.' &>/dev/null &');
					}
					else
					{
						print "change to closed\n";
						system('wget --no-check-certificate -q -O /dev/null '.$url_door_closed.' &>/dev/null &');
					}
				}
			}
		}
	} until(0); #until (eof $fifo or eof $ttyusb);
	print("eof\n");
	if (eof $fifo) {print "eof fifo\n"; close($fifo); $fifo=undef; print "closed fifo\n";}
	if (eof $ttyusb) {print "eof ttyusb\n"; close($ttyusb); $ttyusb=undef; print "closed ttyusb\n";}
}

sub handle_cmd
{
	my $cmd = shift;
	my $who = shift;
	print "c:'$cmd' w:'$who'\n";
	my $tuer=$main::tuer_status;
	if    ($cmd eq "open")   { $tuer=$main::door_open; }
	elsif ($cmd eq "close")  {$tuer=$main::door_closed; }
	elsif ($cmd eq "toggle") {$tuer= !$tuer;}
	elsif ($cmd eq "log") {door_log($who)}
	else {door_log("Invalid Command: $cmd $who")}
	
	if (not $tuer == $main::tuer_status)
	{
		if ($tuer == $main::door_open)
		{
			door_log("Door opened by $who");
			print $ttyusb "o";
			system('wget --no-check-certificate -q -O /dev/null '.$url_door_open.' &>/dev/null &');
		}
		else
		{
			door_log("Door closed by $who");
			print $ttyusb "c";
			system('wget --no-check-certificate -q -O /dev/null '.$url_door_closed.' &>/dev/null &');
		}
		
	}	
}
