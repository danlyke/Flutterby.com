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
use Flutterby::Spamcatcher;

sub main
{
    my ($cgi, $dbh,$cookie, $userinfo,$loginerror);
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

    $dbh = DBI->connect($configuration->{-database},
						$configuration->{-databaseuser},
						$configuration->{-databasepass})
		or die $DBI::errstr;
	$dbh->{AutoCommit} = 1;

    ($cookie,$userinfo,$loginerror) = Flutterby::Users::GetCookieAndLogin($cgi,$dbh);
    my ($variables);
    $variables = Flutterby::Users::GetWeblogInfo($cgi, $dbh);

    my ($sql, $wikiid, $wikiterm);

    if (defined($cgi->param('wikiid')))
    {
	$sql = 'SELECT id, term FROM wiki WHERE id='.$dbh->quote($cgi->param('wikiid'));

	($wikiid,$wikiterm) = $dbh->selectrow_array($sql);
	$cgi->param('id' => $wikiterm);
    }
    elsif (defined($cgi->param('id')))
    {
	my $idprocessed = $cgi->param('id');
	$idprocessed =~ s/\s+/ /sg;
	$idprocessed =~ s/^[\s\:\;\,\.\",!\@\#\$\%\^\&\*]*//sg;
	$idprocessed =~ s/[\s\:\;\,\.\",!\@\#\$\%\^\&\*]$//sg;

	$sql = 'SELECT id, term FROM wiki WHERE upper(term)=upper('.$dbh->quote($idprocessed).')';

	($wikiid,$wikiterm) = $dbh->selectrow_array($sql);
	$cgi->param('id' => $wikiterm) unless defined($cgi->param('id'));
	unless ($wikiid)
	{
	    if (defined($userinfo->{'id'})
		&& $userinfo->{'addwiki'})
	    {
		$sql = 'INSERT INTO wiki(term) VALUES ('.$dbh->quote($idprocessed).')';
		$dbh->do($sql)
		    || die $dbh->errstr;
		$sql = 'SELECT * FROM wiki WHERE term='.$dbh->quote($idprocessed);
		($wikiid) = $dbh->selectrow_array($sql);
	    }
	}
    }

    if (defined($userinfo->{'id'}) && $userinfo->{'editwiki'} &&
	$cgi->param('_article_id'))
    {
	unless (defined($userinfo->{'id'}))
	{
	    my (%h);
	    $h{-cookie} = $cookie if ($cookie);
	    print $cgi->header(%h);
	    $cgi->param('wikiid' => $wikiid) if defined($wikiid);
	    print '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "DTD/xhtml1-transitional.dtd">';
	    Flutterby::Users::PrintLoginScreen($configuration,
					     $cgi, 
					     $dbh,
					     '/archives/wiki.cgi',
					     $loginerror);
	    return;
	}

	my (@a);
	foreach ('text', 'texttype', 'title')
	{
	    push @a, "$_=".$dbh->quote($cgi->param('_'.$_))
		if (defined($cgi->param('_'.$_)));
	}
	$sql = 'UPDATE articles SET '
	    .join(', ', @a)
	    .' WHERE articles.id='.$dbh->quote($cgi->param('_article_id'));
	$dbh->do($sql) or die $dbh->errstr;
    }
    elsif (defined($cgi->param('_text'))
	   && defined($cgi->param('_texttype'))
	   && defined($cgi->param('_title')))
    {
	unless (defined($userinfo->{'id'}))
	{
	    my (%h);
	    $h{-cookie} = $cookie if ($cookie);
	    $cgi->param('wikiid' => $wikiid) if defined($wikiid);
	    print $cgi->header(%h);
	    print '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "DTD/xhtml1-transitional.dtd">';
	    Flutterby::Users::PrintLoginScreen($configuration,
					     $cgi, 
					       $dbh,
					     '/archives/wiki.cgi',
					     $loginerror);
	    return;
	}
	my ($ordervalue);

	$ordervalue = $cgi->param('_displayorder');
	print STDERR "Display order is $ordervalue\n";

	if (!defined($ordervalue) || $ordervalue <= 0)
	{
	    $sql = 'SELECT COALESCE(max(displayorder),10) FROM wikientries WHERE wiki_id='.$dbh->quote($wikiid);
	    ($ordervalue) = $dbh->selectrow_array($sql);
	    $ordervalue += 10;
	}
	else
	{
	    my ($lowerordervalue);
	    $sql = 'SELECT displayorder FROM wikientries WHERE wiki_id='.$dbh->quote($wikiid)
		.' AND displayorder < '.$dbh->quote($ordervalue)
		.' ORDER DESC LIMIT 1';
	    ($lowerordervalue) = $dbh->selectrow_array($sql);
	    $lowerordervalue = 0 unless ($lowerordervalue);
	    $ordervalue = ($ordervalue + $lowerordervalue) / 2;
	    
	}

	my ($id) = $dbh->selectrow_array("SELECT nextval('articles_id_seq')");
	Flutterby::DBUtil::escapeFieldsToEntities($cgi, '_text');

	$sql = 'INSERT INTO articles (id, author_id, trackrevisions, text,texttype,title) VALUES ('
	    ."$id, $userinfo->{'id'}, 'true', "
	    .$dbh->quote($cgi->param('_text')).','
	    .$dbh->quote($cgi->param('_texttype')).','
	    .$dbh->quote($cgi->param('_title')).')';
	$dbh->do($sql) or die $dbh->errstr;
	$sql = 'INSERT INTO wikientries(displayorder,wiki_id, article_id) VALUES ('
	    .$dbh->quote($cgi->param('_displayorder'))
	    .','
	    .$dbh->quote($wikiid)
	    .','
	    .$dbh->quote($id)
	    .')';
	$dbh->do($sql) or die $dbh->errstr();
	$dbh->commit();
    }
    $variables->{'userinfo_id'} = 0;
    $variables->{'userinfo_id'} = $dbh->quote($userinfo->{'id'})
	if (defined($userinfo->{'id'}));
    $variables->{'textentryrows'} = $userinfo->{'textentryrows'} || 16;
    $variables->{'textentrycols'} = $userinfo->{'textentrycols'} || 80;


    if (defined($wikiid))
    {
	my ($tree) =
	    Flutterby::HTML::LoadHTMLFileAsTree($configuration->{-htmlpath}.'wiki.html');
	my ($out, $formatters);
	$variables->{'wikiid'} = $wikiid;
	$variables->{'wikiterm'} = $wikiterm;
	$variables->{'sqlquotedwikiterm'} = $dbh->quote($wikiterm);
	$formatters =
	{
	    1 => new Flutterby::Parse::Text,
	    2 => new Flutterby::Parse::HTML,
	    'escapehtml' => new Flutterby::Parse::String,
	};
	my (%h,@blogentries,$lastmodified);
	$h{-cookie} = $cookie if ($cookie);
	print $cgi->header(%h);
	print '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "DTD/xhtml1-transitional.dtd">';
	
	$out = new Flutterby::Output::HTMLProcessed
	    (
	     -classcolortags => $configuration->{-classcolortags},
	     -colorschemecgi => $cgi,
	     -dbh => $dbh,
	     -variables => $variables,
	     -textconverters => $formatters,
	     -cgi => new CGI('id='.$cgi->param('id')),
	     );
	$out->output($tree);
    }
    else
    {
	my $tree;

	if ($cgi->param('bydate'))
	{
	    $tree = Flutterby::HTML::LoadHTMLFileAsTree($configuration->{-htmlpath}.'wikislastmodified.html');
	}
	else
	{
	    $tree = Flutterby::HTML::LoadHTMLFileAsTree($configuration->{-htmlpath}.'wikis.html');
	}
	my ($out, $formatters);
	$formatters =
	{
	    1 => new Flutterby::Parse::Text,
	    2 => new Flutterby::Parse::HTML,
	    'escapehtml' => new Flutterby::Parse::String,
	};
	my (%h,@blogentries,$lastmodified);
	$h{-cookie} = $cookie if ($cookie);
	print $cgi->header(%h);
	print '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "DTD/xhtml1-transitional.dtd">';

	$out = new Flutterby::Output::HTMLProcessed
	    (
	     -classcolortags => $configuration->{-classcolortags},
	     -colorschemecgi => $cgi,
	     -dbh => $dbh,
	     -variables => $variables,
	     -textconverters => $formatters,
	     -cgi => new CGI('id='.$cgi->param('id')),
	     );
	$out->output($tree);
    }
    $dbh->disconnect();
}

main();
