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
	foreach ($cgi->param)
	  {

	    if (/^_newtopic\!/)
	      {
		my ($sql) = 'INSERT INTO articletopics (topic) VALUES ('
		  .$dbh->quote($cgi->param($_)).')';
		$dbh->do($sql)
		  || print STDERR "$sql\n".$dbh->errstr;
	      }
	    elsif (/^_delterm\!(.*)$/)
	      {
		my ($sql) = 'DELETE FROM articletopicterms WHERE topic_id='
		  .$dbh->quote($cgi->param('_topic_id')).' AND text='
		    .$dbh->quote($1);
		$dbh->do($sql)
		  || print STDERR "$sql\n".$dbh->errstr;
	      }
	    elsif (/^_newterm\!/ && ($cgi->param($_) ne ''))
	      {
		my ($sql) = 'INSERT INTO articletopicterms (topic_id,text) VALUES ('
		  .join(',',
			$dbh->quote($cgi->param('_topic_id')),
			$dbh->quote($cgi->param($_))).')';
		$dbh->do($sql)
		  || print STDERR "$sql\n".$dbh->errstr;
	      }
	  }


	my ($query);
	$query = '';
	my ($tree); 
	if (defined($cgi->param('id')))
	  {
	    $query = $cgi->param('id');
	    $tree =
	      Flutterby::HTML::LoadHTMLFileAsTree($configuration->{-htmlpath}.'edittopic.html');
	  }
	else
	  {
	    $tree =
	      Flutterby::HTML::LoadHTMLFileAsTree($configuration->{-htmlpath}.'edittopics.html');
	  }

	my ($variables);
	$variables = Flutterby::Users::GetWeblogInfo($cgi, $dbh);
	$variables->{'userinfo_id'} = $dbh->quote($userinfo->{'id'});
	$variables->{'queryterms'} = $query;
	
	my ($out);
	$out = new Flutterby::Output::HTMLProcessed
	  (
	   -classcolortags => $configuration->{-classcolortags},
	   -colorschemecgi => $cgi,
	   -dbh => $dbh,
	   -variables => $variables,
	   -textconverters => 
	   { 
	    'escapehtml' => new Flutterby::Parse::String,
	   },
	   -cgi =>
	   {
	    './edittopics.cgi' =>
	    {
	     -cgi => $cgi,
	     -action => 
	     Flutterby::Util::buildGETURL('./edittopics.cgi',$cgi),
	    }
	   }
	  );
	$out->output($tree);

      }
    else
      {
	Flutterby::Users::PrintLoginScreen($configuration,
					   $cgi, 
					   $dbh, 
					   './edittopics.cgi',
					   $loginerror);
      }
    $dbh->disconnect;
  }
&main;
