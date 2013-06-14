#!/usr/bin/perl -w
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
    my ($cgi, $dbh,$userinfo);
    $dbh = DBI->connect($configuration->{-database},
			$configuration->{-databaseuser},
			$configuration->{-databasepass})
      or die $DBI::errstr;
	$dbh->{AutoCommit} = 1;
    $cgi = new CGI;

    print $cgi->header();
    print '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "DTD/xhtml1-transitional.dtd">';
    my ($tree) = 
      Flutterby::HTML::LoadHTMLFileAsTree($configuration->{-htmlpath}.'commenthistory.html');
    
    my ($variables);
    $variables = Flutterby::Users::GetWeblogInfo($cgi, $dbh);
    $variables->{'commentid'} = $cgi->param('id');

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
    $dbh->disconnect();
  }
&main;
