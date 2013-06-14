#!/usr/bin/perl -w
use strict;
use CGI;
#use CGI::Carp qw(fatalsToBrowser);
use DBI;
use lib 'flutterby_cms';
use vars qw($configuration);
use Flutterby::Config;
$configuration ||= Flutterby::Config::load();
use Flutterby::HTML;
use Flutterby::Output::HTMLProcessed;
use Flutterby::Parse::HTML;
use Flutterby::Parse::Text;
use Flutterby::Parse::String;
use Flutterby::Users;
use Flutterby::DBUtil;

sub main
  {
    my ($cgi, $dbh,$userinfo,$loginerror);
    $dbh = DBI->connect($configuration->{-database},
			$configuration->{-databaseuser},
			$configuration->{-databasepass})
      or die $DBI::errstr;
	$dbh->{AutoCommit} = 1;
    $cgi = new CGI;

    ($userinfo,$loginerror) = Flutterby::Users::CheckLogin($cgi,$dbh);

    if (defined($userinfo->{'id'}) && $userinfo->{'addblogentries'})
    {
	my ($tree) = 
	  Flutterby::HTML::LoadHTMLFileAsTree( $configuration->{-htmlpath}.'newarticle.html');
	my ($out);
	$out = new Flutterby::Output::HTMLProcessed
	  (
	   -classcolortags => $configuration->{-classcolortags},
	   -colorschemecgi => $cgi,
	   -dbh => $dbh,
	   -textconverters => 
	   { 
	    0 => new Flutterby::Parse::Text,
	    1 => new Flutterby::Parse::HTML,
	    2 => new Flutterby::Parse::Text,
	    'escapehtml' => new Flutterby::Parse::String,
	   },
	   -cgi => $cgi
	  );
	$out->output($tree);
    }
    else
    {
	Flutterby::Users::PrintLoginScreen($configuration,
					   $cgi, 
					   $dbh,
					   './newarticle.cgi',
					   $loginerror);
    }
    $dbh->disconnect;
  }
&main;
