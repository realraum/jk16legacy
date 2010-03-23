#!/usr/bin/perl -w
#
#

use strict;
use utf8;
require LWP::UserAgent;
my $ua = LWP::UserAgent->new(env_proxy => 1,
                              keep_alive => 1,
                              timeout => 30,
                             );
use HTTP::Cookies;
use LWP;
$ua->cookie_jar({});

###############
$sensor::url_refresh = "http://slug.realraum.at/cgi-bin/sensor-temp.cgi";
$sensor::url_image = "http://slug.realraum.at/temp0.png";
$sensor::localpath = "/tmp/temp0.png";
$sensor::mintime = 0.0015;
###############

sub output_saved_image
{
  return 0 if ( not -e $sensor::localpath);
  my $fh;  
  print STDOUT "Content-type: image/png\n\n";
  open($fh,"<$sensor::localpath") or exit;
  while (<$fh>) {print $_};
  close($fh);
  return 1;
}

sub output_remote_image_and_save
{
  my $response;
  $response = $ua->get($sensor::url_refresh);
  return 0 unless (defined $response);
  $response = $ua->get($sensor::url_image);
  if (defined $response and $response->content =~ /^\x89PNG/)
  {
    my $fh;
    open($fh,">$sensor::localpath");
    print $fh $response->content;
    close($fh);
    print STDOUT "Content-type: image/png\n\n";
    print $response->content;
    $response->clear;
    return 1;
  }
  return 0;
}

sub output_error
{
  print STDOUT "Status: 404 Not Found\n";
  print STDOUT "Content-type: text/html\n\n";
  print STDOUT "<html><body><h1>Sorry</h1><h2>The picture you requested could not be found</h2></body></html>\n"; 
  return 1;
}

if (-e $sensor::localpath and -M $sensor::localpath < $sensor::mintime)
{
  exit if (&output_saved_image);
}
else
{
  exit if (&output_remote_image_and_save);
  exit if (&output_saved_image);
}
&output_error;
