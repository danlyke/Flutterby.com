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


my (@editablefields) =
  (
   'email',
   'password',
   'homepage_url',
   'weblog_url',
   'weblog_name',
   'adbanner_url',
   'bio_text',
   'bio_texttype',
   'emailverified',
  );

sub main
  {
    my ($cgi, $dbh,$userinfo);
    $dbh = DBI->connect($configuration->{-database},
			$configuration->{-databaseuser},
			$configuration->{-databasepass})
      or die $DBI::errstr;
	$dbh->{AutoCommit} = 1;
    $cgi = new CGI;

    $userinfo = Flutterby::Users::CheckLogin($cgi,$dbh);

    if (defined($cgi->param('id')))
      {
	my ($terms);

	$terms = join(' OR ',
		      map 
		      {
			'id='.$dbh->quote($_);
		      }	split(',',$cgi->param('id')));

	my ($tree) = 
	  Flutterby::HTML::LoadHTMLFileAsTree($configuration->{-htmlpath}.'user.html');
    
	my ($variables);
	$variables = Flutterby::Users::GetWeblogInfo($cgi, $dbh);
	$variables->{'conditions'} = $terms;
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
	  );
	$out->output($tree);
      }
    else
      {
	my ($tree) = 
	  Flutterby::HTML::LoadHTMLFileAsTree($configuration->{-htmlpath}.'userlist.html');
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
	  );
	$out->output($tree);
      }
    $dbh->disconnect;
  }
&main;
