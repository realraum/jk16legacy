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
$main::tuer_future_status=$main::tuer_status;
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

my $read_set = new IO::Select();

sub open_fifo
{
	#print "open fifo\n"; 
	sysopen($fifo,$fifofile, O_RDONLY | O_NONBLOCK); 
	#print "x\n";
	 $read_set->add($fifo); 
}

sub open_usb
{
	#print "open usb\n";
	sysopen($ttyusb, $door_ttyusb_dev, O_RDWR | O_NONBLOCK); 
	$ttyusb->autoflush(1);
	my $termios = POSIX::Termios->new;
	$termios->getattr(fileno $ttyusb);
	$termios->setispeed( &POSIX::B9600 );
	$termios->setospeed( &POSIX::B9600 );
	#$termios->setcflag( $termios->getcflag & ~(&POSIX::PARENB | &POSIX::PARODD) & (~&POSIX::CSIZE | &POSIX::CS8));
	$termios->setattr(fileno $ttyusb);
	#print "x\n";
	$read_set->add($ttyusb); 
}

sub close_fifo
{
	$read_set->remove($fifo);
	close($fifo);
}

sub close_usb
{
	$read_set->remove($ttyusb);
	close($ttyusb);
}

&open_usb;
&open_fifo;

print $ttyusb "s";
	 
while(1)
{
	my ($rh_set) = IO::Select->select($read_set, undef, undef);
	#print "tuer_status_start: ".$main::tuer_status,"\n";
	foreach my $fh (@$rh_set)
	{
		if ($fh == $fifo)
		{
			my $fifo_msg = <$fh>;
			unless ($fifo_msg)
			{
				close_fifo();
				#sleep(0.1);
				open_fifo();
				last;
			}
			if ($fifo_msg =~ /^(\w+)\s*(.*)/) 
			{
				handle_cmd($1,$2);
			}
		}
		elsif ($fh == $ttyusb)
		{
			my $ttyusb_msg = <$fh>;
			last unless ($ttyusb_msg);
			#print($ttyusb_msg);
			door_log($door_ttyusb_dev.": ".$ttyusb_msg);
			if ($ttyusb_msg =~ /took too long!/)
			{
				door_log("Got '".$ttyusb_msg."'.  Sending Reset..");
				print $ttyusb "r";
				$main::tuer_status=$main::door_closed;
				$main::tuer_future_status=$main::tuer_status;
				last;
			}			
			$main::tuer_status = $main::tuer_future_status if $ttyusb_msg =~ /^Ok/;
			my $tuer=$main::tuer_status;
			$tuer=$main::door_open if $ttyusb_msg =~ /open/;
			$tuer=$main::door_closed if $ttyusb_msg =~ /close|closing/;
			if (not $tuer == $main::tuer_status)
			{
				$main::tuer_status=$tuer;
				if ($tuer == $main::door_open)
				{
					#print "change to open\n";
					system('wget --no-check-certificate -q -O /dev/null '.$url_door_open.' &>/dev/null &');
				}
				else
				{
					#print "change to closed\n";
					system('wget --no-check-certificate -q -O /dev/null '.$url_door_closed.' &>/dev/null &');
				}
			}
		}
	}
	#print "tuer_status_end: ".$main::tuer_status,"\n------------\n";
}

sub handle_cmd
{
	my $cmd = shift;
	my $who = shift;
	#print "c:'$cmd' w:'$who'\n";
	my $tuer=$main::tuer_status;
	if    ($cmd eq "open")   { $tuer=$main::door_open; }
	elsif ($cmd eq "close")  {$tuer=$main::door_closed; }
	elsif ($cmd eq "toggle") {$tuer= !$tuer;}
	elsif ($cmd eq "log") {door_log($who)}
	else {door_log("Invalid Command: $cmd $who")}
	
	if (not $tuer == $main::tuer_status)
	{
		$main::tuer_future_status=$tuer;
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
