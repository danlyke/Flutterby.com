#!/usr/bin/perl -w

use strict;
use CGI;
use CGI::Carp qw(fatalsToBrowser);

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
use Flutterby::Spamcatcher;

sub main
  {
    my ($cgi, $dbh,$userinfo);
    $cgi = new CGI;

    if (Flutterby::Spamcatcher::IsSpamReferer($ENV{'HTTP_REFERER'}))
    {
	my $dest = "http://$ENV{'SERVER_NAME'}$ENV{'REQUEST_URI'}";;
	print $cgi->header();
	print $cgi->header();
	print "<html><head>\n";
	print "<title>Please continue...</title>\n";
	print "</head>\n";
	print "<body><h1>Please continue...</h1>\n";
	print "<p>We're sorry, but due to excessive load from referrer\n";
	print "spammers, we no longer allow direct access to all pages\n";
	print "from certain outside links.</p>\n";
	print "<p>We'll let you continue on to that link in a moment, but\n";
	print 'you can also go to <a href="http://www.flutterby.com/">the';
	print " front page</a>. But you probably just want to go to\n";
	print '<a href="http://www.flutterby.com/archives/browsetopics.cgi?id=';
	print $dest;
	print '">your original destination</a>.';
	print "\n</body></html>\n";
	return;
    }

    if (defined($cgi->param('id'))
	&& defined($ENV{'HTTP_REFERER'})
	&& $ENV{'HTTP_REFERER'} ne ''
	&& $ENV{'HTTP_REFERER'} !~ /flutterby.com/)
    {
	my $dest = $cgi->param('id');
	$dest =~ s/[^0-9\,]//g;
	print $cgi->header();
	print "<html><head>\n";
	print "<title>Please continue...</title>\n";
	print "</head>\n";
	print "<body><h1>Please continue...</h1>\n";
	print "<p>We're sorry, but due to excessive load from referrer\n";
	print "spammers, we no longer allow direct access to the topics\n";
	print "from outside links.</p>\n";
	print "<p>We'll let you continue on to that link in a moment, but\n";
	print 'you can also go to <a href="http://www.flutterby.com/">the';
	print " front page</a>. But you probably just want to go to\n";
	print '<a href="http://www.flutterby.com/archives/browsetopics.cgi?id=';
	print $dest;
	print '">your original destination</a>.';
	print "\n</body></html>\n";
	return;
    }

    $dbh = DBI->connect($configuration->{-database},
			$configuration->{-databaseuser},
			$configuration->{-databasepass})
      or die $DBI::errstr;
	$dbh->{AutoCommit} = 1;

    $userinfo = Flutterby::Users::CheckLogin($cgi,$dbh);

    
    my ($query);
    $query = join(' OR ',
		  map
		  {
		    'blogentries.id='.$dbh->quote($_);
		  } (split (/\,/,$cgi->param('entry_id'))))
      if (defined($cgi->param('entry_id')));
    $query = join(' OR ',
		  map
		  {
		    'articletopiclinks.topic_id='.$dbh->quote($_);
		  } (split (/\,/,$cgi->param('id'))))
      if (defined($cgi->param('id')));
    my ($topictermsquery);
    $topictermsquery = join(',',(split (/\,/,$cgi->param('id'))));

    my ($tree);

    if (defined($query) && $query ne '')
      {
	$tree = Flutterby::HTML::LoadHTMLFileAsTree($configuration->{-htmlpath}.'browsetopic.html');
      }
    else
      {
	$tree = Flutterby::HTML::LoadHTMLFileAsTree($configuration->{-htmlpath}.'browsetopics.html');
      }

    my ($variables);
    $variables = Flutterby::Users::GetWeblogInfo($cgi, $dbh);
    $variables->{'fcmsweblog_id'} = Flutterby::Users::GetWeblogID($cgi->url(), $dbh);
    $variables->{'userinfo_id'} = $dbh->quote($userinfo->{'id'});
    $variables->{'userinfo_editblogentries'} = $dbh->quote($userinfo->{'editblogentries'});
    $variables->{'topictermsquery'} = $topictermsquery;
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
	1 => new Flutterby::Parse::Text,
	2 => new Flutterby::Parse::HTML,
	'escapehtml' => new Flutterby::Parse::String,
       },
       -cgi => $cgi
      );
    $out->output($tree);
    $dbh->disconnect;
  }
&main;




