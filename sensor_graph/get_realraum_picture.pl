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
$cam::url = "http://slug.realraum.at:8088/?action=snapshot";
#$cam::get = {action=>"snapshot"};
$cam::localpath = "/tmp/realraum.jpg";
$cam::mintime = 0.00025;
###############

sub output_saved_image
{
  return 0 if ( not -e $cam::localpath);
  my $fh;  
  print STDOUT "Content-type: image/jpeg\n\n";
  open($fh,"<$cam::localpath") or exit;
  while (<$fh>) {print $_};
  close($fh);
  return 1;
}

sub output_remote_image_and_save
{
  my $response;
  $response = $ua->get($cam::url);
  if (defined $response and $response->content =~ /^\xff\xd8/)
  {    
    my $fh;
    open($fh,">$cam::localpath");
    print $fh $response->content;
    close($fh);
    print STDOUT "Content-type: image/jpeg\n\n";
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

if (-e $cam::localpath and -M $cam::localpath < $cam::mintime)
{
  exit if (&output_saved_image);
}
else
{
  exit if (&output_remote_image_and_save);
  exit if (&output_saved_image);
}
&output_error;
