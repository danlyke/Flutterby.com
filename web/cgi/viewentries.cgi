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
use Flutterby::Output::HTML;
use Flutterby::Parse::HTML;
use Flutterby::Parse::Text;
use Flutterby::Parse::String;
use Flutterby::Users;
use Flutterby::Util;
use Flutterby::DBUtil;


use HTTP::Date;

sub LoadEntriesToArray
  {
    my ($dbh, $array, $textconverters,$variables) = @_;

    my $formats =
      {
       'text' => 'texttype',
       'subject' => 'escapehtml',
       'name' => ' escapehtml'
      };

    my $outputhtml = new Flutterby::Output::HTML();

    my ($sql, $sth, $row, $latest);
    $latest = '';

    {
      $sql = <<'EOT'
SELECT
 weblogentries.id AS blogentry_id,
 articles.entered AS entered, 
 articles.updated AS updated,
 weblogentries.latestcomment AS latestcomment,
 articles.id AS article_id,
 articles.text AS text,
 articles.texttype AS texttype,
 articles.title AS subject,
 articles.author_id AS author_id,
 weblogentries.commentcount AS commentcount,
 users.name AS name,
 CASE 
   WHEN articles.author_id=$userinfo_id OR $userinfo_editblogentries='1' THEN
    '[<a href="/archives/editentry.cgi?id='||weblogentries.id||'">edit</a>]'
   ELSE 
    '' 
   END
 AS editweblogentry,
 '' AS deleteweblogentry,
 'escapehtml' AS escapehtml
FROM users, weblogentries, articles WHERE articles.id=weblogentries.article_id 
AND not weblogentries.ignorepost
AND(users.id=articles.author_id and ($queryterms))
ORDER BY entered LIMIT 250
EOT
    }
    $sql = Flutterby::Util::subst($sql,$variables);
    $sth = $dbh->prepare($sql) 
      || die $dbh->errstr."\n$sql";
    $sth->execute
      || die $sth->errstr."\n$sql";
    while ($row = $sth->fetchrow_hashref)
      {
	foreach (keys %$formats)
	  {
	    if (defined($row->{$_})
		and defined($row->{$formats->{$_}})
		and defined($textconverters->{$row->{$formats->{$_}}}))
	      {
		my ($t) = '';
		my ($tree,$node,@tree);
		$outputhtml->setOutput(\$t);
		$tree = $textconverters->{$row->{$formats->{$_}}}
		  ->parse($row->{$_});
		if ($node = Flutterby::Tree::Find::nodeChildInfo($tree,'body'))
		  {
		    @tree = @$node;
		    shift @tree;
		    $outputhtml->output(\@tree);
		  }
		else
		  {
		    $outputhtml->output($tree);
		  }
		$row->{$_} = $t;
	      }
	  }

	push @$array, $row;
	$latest = $row->{'entered'} if ($row->{'entered'} gt $latest);
	$latest = $row->{'updated'} if ($row->{'updated'} gt $latest);
	$latest = $row->{'latestcomment'} if (defined($row->{'latestcomment'}) 
					      && $row->{'latestcomment'}
					      gt $latest);
      }
    if ($latest ne '')
      {
	$latest = time2str(str2time($latest));
      }
    else
      {
	$latest = undef;
      }
    return $latest;
  }

sub DumpRefTree
  {
    my ($r, $depth) = @_;
    $depth = 0 unless ($depth);
    
    print ' 'x$depth."$r\n";
    if (ref($r))
      {
	if (ref($r) eq 'ARRAY')
	  {
	    foreach (@$r)
	      {
		DumpRefTree($_,$depth + 1);
	      }
	  }
	if (ref($r) eq 'HASH')
	  {
	    $depth++;
	    
	    foreach (keys %$r)
	      {
		print ' 'x$depth."$_\n";
		DumpRefTree($r->{$_},$depth + 1);
	      }
	  }

      }
  }

sub main
{
    my ($cgi, $dbh,$userinfo,$loginerror,$continue,$cookie, $pagetitle);
    $dbh = DBI->connect($configuration->{-database},
			$configuration->{-databaseuser},
			$configuration->{-databasepass})
      or die DBI::errstr;
	$dbh->{AutoCommit} = 1;
    $cgi = new CGI;

    ($cookie,$userinfo,$loginerror) = Flutterby::Users::GetCookieAndLogin($cgi,$dbh);

    my ($query,$limit);
    $limit = '';
    $query = join(' OR ',
		  map
		  {
		      'weblogentries.id='.$dbh->quote($_);
		  } (split (/\,/,$cgi->param('entry_id'))))
	if (defined($cgi->param('entry_id')));
    $query = join(' OR ',
		  map
		  {
		      'weblogentries.id='.$dbh->quote($_);
		  } (split (/\,/,$cgi->param('id'))))
	if (defined($cgi->param('id')));
    if (defined($cgi->param('fromdate'))
	|| defined($cgi->param('todate')))
    {
	$pagetitle = "From ".$cgi->param('fromdate');
	$pagetitle .= " to ".$cgi->param('todate')
	    if (defined($cgi->param('todate')));

	my ($f,$t);
	$query .= 'articles.entered >= '.$dbh->quote($cgi->param('fromdate').' 00:00:00')
	    if (defined($cgi->param('fromdate')));
	$query .= ' and ' if (defined($cgi->param('fromdate'))
			     && defined($cgi->param('todate')));
	$query .= 'articles.entered <= '.$dbh->quote($cgi->param('todate').' 23:59:59')
	    if (defined($cgi->param('todate')));
    }
    
    unless (defined($query))
    {
	my ($maxid) = $dbh->selectrow_array("SELECT MAX(id) FROM weblogentries");
	$query = 'weblogentries.id='.int(rand($maxid));
    }

    my ($tree) =
      Flutterby::HTML::LoadHTMLFileAsTree($configuration->{-htmlpath}.'viewentries.html');
    my ($out, $variables,$formatters);
    $variables = Flutterby::Users::GetWeblogInfo($cgi, $dbh);

    $variables->{'userinfo_id'} = $dbh->quote($userinfo->{'id'});
    $variables->{'userinfo_editblogentries'} = $dbh->quote($userinfo->{'editblogentries'});
    $variables->{'queryterms'} = $query;
    $variables->{'limitterms'} = $limit;

    $formatters =
    {
	1 => new Flutterby::Parse::Text,
	2 => new Flutterby::Parse::HTML,
	'escapehtml' => new Flutterby::Parse::String,
    };
    my (%h,@blogentries,$lastmodified);
    $lastmodified = LoadEntriesToArray($dbh,\@blogentries,$formatters,$variables);

    if (!defined($pagetitle))
    {
	my $i;
	$pagetitle = '';
	for ($i = 0; $i < 5 && $i < @blogentries; $i++)
	{
	    $pagetitle = "$pagetitle $blogentries[$i]->{subject} $blogentries[$i]->{entered}";
	}
	$pagetitle = "$pagetitle..." if (@blogentries > $i);
    }
    $variables->{'pagetitle'} = $pagetitle;

    $h{-cookie} = $cookie if ($cookie);
    $h{-Last_Modified} = $lastmodified if ($lastmodified);
    print $cgi->header(%h);
    print '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "DTD/xhtml1-transitional.dtd">';

    unless (defined($cgi->request_method()) && $cgi->request_method() eq 'HEAD')
    {
	$variables->{'blogentries'} = \@blogentries;
	my $entryid = $cgi->param('id');
	$entryid = '' unless(defined($entryid));
	$out = new Flutterby::Output::HTMLProcessed
	    (
	     -dbh => $dbh,
	     -variables => $variables,
	     -textconverters => $formatters,
	     -cgi => new CGI('id='.$entryid),
	     );
	$out->output($tree);
    }
    $dbh->disconnect;
}
&main;
