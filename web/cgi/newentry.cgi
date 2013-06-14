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
use Flutterby::Output::SHTMLProcessed;
use Flutterby::Parse::Ordinal;
use Flutterby::Parse::Int;
use Flutterby::Parse::Month;
use Flutterby::Parse::DayOfWeek;

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

    if (defined($userinfo->{'id'}))
    {
    	if ($userinfo->{'addarticles'}
	    && defined($cgi->param('_publish_id'))
	    && defined($cgi->param('_publish_title'))
	    && defined($cgi->param('_publishcategory_id')))
	{
	    my ($publishcategory, $publishtitle, $publishid);
	    $publishcategory = $cgi->param('_publishcategory_id');
	    $publishtitle = $cgi->param('_publish_title');
	    $publishid = $cgi->param('_publish_id');

	    my ($rootdirectory, $filenameformat,$templatehtml,$sql);
	    $sql = 'SELECT rootdirectory, filenameformat, templatehtml FROM articlecategories WHERE id='.$dbh->quote($publishcategory);

	    ($rootdirectory, $filenameformat,$templatehtml)
		= $dbh->selectrow_array($sql);
	    if (defined($rootdirectory) && defined($filenameformat))
	    {
		my ($title, $fulltitle);
		$title = $publishtitle;
		$fulltitle = $title;
		$title =~ s/\W//sg;
		my ($Day, $Mon, $dd, $hh,$mm,$ss,$yyyy);

		($Day, $Mon, $dd, $hh,$mm,$ss,$yyyy) = 
		    (localtime(time)
		     =~ /(\w+)\s+(\w+)\s+(\d+)\s+(\d+)\:(\d+)\:(\d+)\s+(\d+)/);


		my (%vars) =
		    (
		     'yyyy' => $yyyy,
		     'Mon' => $Mon,
		     'dd' => $dd,
		     'title' => $title,
		     );
		my ($outputfilename) =
		    $rootdirectory.Flutterby::Util::subst($filenameformat,
							  \%vars).'.html';
		Flutterby::Util::EnsureDirectory($configuration->{-htmlroot}
						 .'/'.$outputfilename);
		my ($tree);
		$tree = Flutterby::HTML::LoadHTMLFileAsTree($configuration->{-htmlpath}.$templatehtml);
		my ($variables);
		$variables = Flutterby::Users::GetWeblogInfo($cgi, $dbh);
		$variables->{'article_ids'} = $publishid;

		if (open O, ">$configuration->{-htmlroot}/$outputfilename.bak")
		{
		    my ($out);
		    $out = new Flutterby::Output::SHTMLProcessed
			(
			 -classcolortags => $configuration->{-classcolortags},
			 -dbh => $dbh,
			 -variables => $variables,
			 -textconverters => 
			 { 
			     1 => new Flutterby::Parse::Text,
			     2 => new Flutterby::Parse::HTML,
			     3 => new Flutterby::Parse::Text,
			     'escapehtml' => new Flutterby::Parse::String(-longeststring => 40),
			     'escapeurl' => new Flutterby::Parse::String(),
			     'month' => new Flutterby::Parse::Month,
			     'day' => new Flutterby::Parse::Ordinal,
			     'dayofweek' => new Flutterby::Parse::DayOfWeek,
			 },
			 );
		    print O '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "DTD/xhtml1-transitional.dtd">';
		    $out->setOutput(\*O);
		    $out->output($tree);
		    close O;
		    chmod 0775, "$configuration->{-htmlroot}/$outputfilename.bak";
		    unless (-f "$configuration->{-htmroot}/$outputfilename")
		    {
			$sql = 'INSERT INTO articlespublished(article_id,category_id, path) VALUES ('
			    .$dbh->quote($publishid).','
			    .$dbh->quote($publishcategory).','
			    .$dbh->quote($outputfilename).')';
			$dbh->do($sql)
			    || warn $dbh->errstr."\n   $sql\n";
		    }
		    rename("$configuration->{-htmlroot}/$outputfilename.bak",
			   "$configuration->{-htmlroot}/$outputfilename");
		}
		else
		{
		    printf STDERR "Unable to open $configuration->{-htmlroot}/$outputfilename.bak for writing\n";
		}

		$cgi = new CGI('');
		$cgi->param('_text' =>
			    "\&lt;a href=\"/$outputfilename\"\&gt;"
			    .$fulltitle
			    .'&lt;/a&gt;');
		$cgi->param('_title' => $fulltitle);
	    }
	}
	if ($userinfo->{'addblogentries'})
	{
	    my ($tree) = 
		Flutterby::HTML::LoadHTMLFileAsTree($configuration->{-htmlpath}.'newentry.html');
	    
	    my ($out);
	    $out = new Flutterby::Output::HTMLProcessed
		(
		 -classcolortags => $configuration->{-classcolortags},
		 -colorschemecgi => $cgi,
		 -variables => {
		     'fcmsweblog_id' => Flutterby::Users::GetWeblogID($cgi, $dbh),
		     'textentryrows' => $userinfo->{'textentryrows'} || 16,
		     'textentrycols' => $userinfo->{'textentrycols'} || 80,
		 },
		 -dbh => $dbh,
		 -textconverters => 
		 { 
		     1 => new Flutterby::Parse::Text,
		     2 => new Flutterby::Parse::HTML,
		     'escapehtml' => new Flutterby::Parse::String,
		 },
		 -cgi => $cgi
		 );
	    $out->output($tree);
	}
      }
    else
    {
	Flutterby::Users::PrintLoginScreen($configuration,
					   $cgi, 
					   $dbh,
					   './newentry.cgi',
					   $loginerror);
    }
    $dbh->disconnect;
}
&main;
