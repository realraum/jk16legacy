#!/usr/bin/perl -w
#
#
use strict;
use utf8;
use CGI;
my $q = CGI->new;
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
$cam::localpath = "/tmp/realraum-freeze.jpg";
###############

sub output_saved_image
{
  return 0 if ( not -e $cam::localpath);
  my $fh;  
  print STDOUT header("image/jpeg");
  open($fh,"<$cam::localpath") or exit;
  while (<$fh>) {print $_};
  close($fh);
  return 1;
}

sub save_remote_image
{
  my $response;
  $response = $ua->get($cam::url);
  if (defined $response and $response->content =~ /^\xff\xd8/)
  {    
    my $fh;
    open($fh,">$cam::localpath");
    print $fh $response->content;
    close($fh);
    
    print STDOUT header("text/html");
    print STDOUT "<html><body>done</body></html>\n";
    return 1;
  }
  return 0;
}

sub output_error
{
  print STDOUT header("text/html","404 Not Found");
  print STDOUT "<html><body><h1>Sorry</h1><h2>The picture you requested could not be found</h2></body></html>\n"; 
  return 1;
}

if ($q->param('freeze') eq "98VB9s")
{
  exit if (&save_remote_image);
}
elsif (-e $cam::localpath and -M $cam::localpath)
{
  exit if (&output_saved_image);
}
&output_error;
