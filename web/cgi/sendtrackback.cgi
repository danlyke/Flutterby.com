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
    my ($variables);
    $variables = Flutterby::Users::GetWeblogInfo($cgi, $dbh);

    ($userinfo,$loginerror) = Flutterby::Users::CheckLogin($cgi,$dbh);

    if (defined($userinfo->{'id'}) && $userinfo->{'addblogentries'})
    {
	if (defined($cgi->param('_trackbackurl'))
	    && defined($cgi->param('_title'))
	    && defined($cgi->param('_excerpt'))
	    && defined($cgi->param('_blog_name'))
	    && defined($cgi->param('_url')))
	{
	    my ($ua);
	    $ua = new LWP::UserAgent(agent
				     => 'FlutterbyTrackbacker/0.01 (http://www.flutterby.net)');
	    
	    my ($response);
	    $response = $ua->post($cgi->param('_trackbackurl'),
				  {
				      'title' => $cgi->param('_title'),
				      'excerpt' => $cgi->param('_excerpt'),
				      'blog_name' => $cgi->param('_blog_name'),
				      'url' => $cgi->param('_url'),
				  }
				  );

	    if ($response->is_success)
	    {
		my ($content);
		$content = $response->content;
		$content =~ s/\&/\&amp;/g;
		$content =~ s/\</\&lt;/g;
		$content =~ s/\>/\&gt;/g;
		$content =~ s/\n/\<br\>/g;
		$variables->{'trackback_status'} = $content;
	    }
	    else
	    {
		$variables->{'trackback_status'} = '<big><strong>Trackback Failed</strong></big>';
	    }

	}
	my ($tree) = 
	  Flutterby::HTML::LoadHTMLFileAsTree($configuration->{-htmlpath}.'sendtrackback.html');
	    
	my ($out);
	$out = new Flutterby::Output::HTMLProcessed
	    (
	     -classcolortags => $configuration->{-classcolortags},
	     -colorschemecgi => $cgi,
	     -variables => $variables
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
