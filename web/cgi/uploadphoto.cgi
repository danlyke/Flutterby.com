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
use Flutterby::Util;
use Flutterby::DBUtil;

sub main
  {
    my ($cgi, $dbh,$userinfo,$loginerror,$continue);
    $dbh = DBI->connect($configuration->{-database},
			$configuration->{-databaseuser},
			$configuration->{-databasepass})
      or die DBI::errstr;
	$dbh->{AutoCommit} = 1;
    $cgi = new CGI;

    ($userinfo,$loginerror) = Flutterby::Users::CheckLogin($cgi,$dbh);
    if (defined($userinfo)
	&& 
	(!defined($cgi->param('_update'))
	 || defined($userinfo->{'id'})))
    {
	my ($tree) =
	  Flutterby::HTML::LoadHTMLFileAsTree($configuration->{-htmlpath}.'uploadphoto.html');
	my ($variables);
	$variables = Flutterby::Users::GetWeblogInfo($cgi, $dbh);
	$variables->{'userinfo_id'} = $dbh->quote($userinfo->{'id'});
	$variables->{'userinfo_editphotoentries'} = $dbh->quote($userinfo->{'editphotoentries'});

	my ($out);
	$out = new Flutterby::Output::HTMLProcessed
	  (
	   -classcolortags => $configuration->{-classcolortags},
	   -colorschemecgi => $cgi,
	   -dbh => $dbh,
	   -variables => $variables,
	   -textconverters => 
	   { 
	       1 => new Flutterby::Parse::Text,
	       2 => new Flutterby::Parse::HTML,
	       'escapehtml' => new Flutterby::Parse::String,
	   },
	   -variables => {
	       'fcmsweblog_id' => Flutterby::Users::GetWeblogID($cgi->url(), $dbh),
	       'textentryrows' => $userinfo->{'textentryrows'} || 16,
	       'textentrycols' => $userinfo->{'textentrycols'} || 80,
	   },

	   );
	$out->output($tree);
    }
    else
    {
        Flutterby::Users::PrintLoginScreen($configuration,
					   $cgi, 
					   $dbh,
					   './photo.cgi',
					   $loginerror);
    }
    $dbh->disconnect;
}
&main;


