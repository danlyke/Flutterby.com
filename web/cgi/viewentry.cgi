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
use Flutterby::Output::HTML;
use Flutterby::Parse::HTML;
use Flutterby::Parse::Text;
use Flutterby::Parse::String;
use Flutterby::Users;
use Flutterby::Util;
use Flutterby::DBUtil;
use Flutterby::Spamcatcher;

use HTTP::Date;


sub LoadAllowCommentsArray($$$$)
{
    my ($dbh,$array,$variables,$row0) = @_;
    my ($sql, $sth, $row, $latest);
    
    $sql = "SELECT now() - '2 weeks'::interval, now() - '7 days'::interval";
    $sth = $dbh->prepare($sql) 
      || die $dbh->errstr;
    $sth->execute
    || die $sth->errstr."\n$sql\n";
    if ($row = $sth->fetchrow_arrayref)
    {
	if ((defined($variables->{'userinfo_entered'})
	     && $row->[0] gt $variables->{'userinfo_entered'})
	    || (defined($row->[1]) && defined($row0->{'entered'})
		&& $row->[1] lt $row0->{'entered'})
	    || (defined($row->[1]) && defined($row0->{'latestcomment'})
		&& $row->[1] lt $row0->{'latestcomment'}))
	{
	    push @$array, ('allowthiscomment', 1);
	}

    }
}

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
 blogentries.id AS blogentry_id,
 blogentries.article_id AS blogentryarticle_id,
 blogentries.entered AS entered, 
 blogentries.updated AS updated,
 CASE WHEN blogentries.updated < NOW()-'1 year'::interval THEN '1' ELSE '0' END AS relequalsnofollow,
 blogentries.latestcomment AS latestcomment,
 blogentries.text AS text,
 blogentries.texttype AS texttype,
 blogentries.subject AS subject,
 blogentries.author_id AS author_id,
 blogentries.commentcount AS commentcount,
 users.name AS name,
 CASE 
   WHEN blogentries.author_id=$userinfo_id OR $userinfo_editblogentries='1' THEN
    '[<a href="/archives/editentry.cgi?id='||blogentries.id||'">edit</a>]'
   ELSE 
    '' 
   END
 AS editweblogentry,
 'escapehtml' AS escapehtml
FROM users, blogentries WHERE (users.id=blogentries.author_id and ($queryterms)) AND NOT blogentries.ignorepost
ORDER BY entered DESC
EOT
    }
    $sql = Flutterby::Util::subst($sql,$variables);
    $sth = $dbh->prepare($sql) 
      || die $dbh->errstr;
    $sth->execute
      || die $sth->errstr."\n$sql\n";
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
                $outputhtml->{-relNoFollow} = $row->{relequalsnofollow};
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
                                              && $row->{'latestcomment'} gt $latest);
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

sub main($)
{
    my ($dbh) = @_;
    my ($cgi, $userinfo,$loginerror,$continue,$cookie);
    $cgi = new CGI;

    if (Flutterby::Spamcatcher::IsSpamReferer($ENV{'HTTP_REFERER'}))
    {
	print $cgi->header('text/plain');
	print "Probably referer spam detected, aborting";
	return;
    }

    if (!defined($cgi->param('id')))
    {
	$cgi->param('id' => $1) if ($ENV{'REQUEST_URI'} =~ /id\=(\d+)/);
	$cgi->param('id' => $1) if ($ENV{'REQUEST_URI'} =~ /\/(\d+)\.htm/);
    }
    if (defined($cgi->param('title'))
	 || defined($cgi->param('url'))
	 || defined($cgi->param('excerpt')))
    {
	print $cgi->header();
	if (defined($cgi->param('title'))
	    && defined($cgi->param('url'))
	    && defined($cgi->param('excerpt'))
	    && defined($cgi->param('id')))
	{
	    my ($sql);
	    $sql = 'INSERT INTO trackbacks(title, url, excerpt, entry_id) VALUES ('
		.join(',', map { $dbh->quote($cgi->param($_)) } ('title','url','excerpt','id'))
		.')';
#	    print "VIEWENTRY: $sql\n";

	    if (0 && $dbh->do($sql))
	    {
		print <<EOF;
<?xml version="1.0" encoding="iso-8859-1"?>
<response>
<error>0</error>
</response>
EOF
            }
	    else
	    {
		print <<EOF;
<?xml version="1.0" encoding="iso-8859-1"?>
<response>
<error>1</error>
<message>$dbh->errstr</message>
</response>
EOF
            }
	}
	else
	{
	    my (@err, $err);
	    foreach ('title','url','excerpt','id')
	    {
		push @err, $_ unless defined($cgi->param($_));
	    }
	    $err = join(', ', @err);

		print <<EOF;
<?xml version="1.0" encoding="iso-8859-1"?>
<response>
<error>1</error>
<message>The following required parameters were not defined: $err</message>
</response>
EOF
	}
	return;
    }
    if (defined($cgi->param('__mode')) && $cgi->param('__mode') eq 'rss' && defined($cgi->param('id')))
    {
	my ($sth, $row, $err, $entryid);
	print $cgi->header;
	$entryid = $cgi->param('id');
	$sth = $dbh->prepare('SELECT title, url, excerpt FROM trackbacks WHERE id='
			     .$dbh->quote($entryid))
	    || die $dbh->errstr;
	$sth->execute || die $sth->errstr;
	print <<EOF;
<?xml version="1.0" encoding="iso-8859-1"?>
<response>
<error>0</error>
<rss version="0.91"><channel>
<title>Flutterby Trackback</title>
<link>http://www.flutterby.com/archives/comments/$entryid.html</link>
<description>Flutterby entry number $entryid</description>
<language>en-us</language>
EOF
	while ($row = $sth->fetchrow_arrayref)
	{
	    print <<EOF;
<item>
<title>$row->[0]</title>
<link>$row->[1]</link>
<description>$row->[2]</description>
</item>
EOF
        }
	print <<EOF;
</channel>
</rss></response>
EOF
        return;
    }

    ($cookie,$userinfo,$loginerror) = Flutterby::Users::GetCookieAndLogin($cgi,$dbh);

    my ($variables);
    $variables = Flutterby::Users::GetWeblogInfo($cgi, $dbh);

    if (defined($cgi->param('unread')))
      {
	if (defined($userinfo->{'id'}))
	  {
	    my ($latestcommentread) = $dbh->quote($userinfo->{'latestcommentread'});
	    $latestcommentread = 'NOW()' if ($cgi->param('unread') eq 'catchup');

	    my ($entryid,$latestcomment) =
	      $dbh->selectrow_array('SELECT id,latestcomment FROM blogentries '
				   .'WHERE (latestcomment>'
				   .$latestcommentread
				   .') ORDER BY latestcomment');
	    if ($entryid)
	    {
		$dbh->do('UPDATE capabilities SET latestcommentread='
			 .$dbh->quote($latestcomment)
			 .' WHERE (user_id='.$dbh->quote($userinfo->{'id'})
			 .'AND weblog_id='
			 .$dbh->quote($variables->{'fcmsweblog_id'}).')');
		my (%h);
		$h{-uri} = "/archives/viewentry.cgi?id=$entryid";
		$h{-cookie} = $cookie if defined($cookie);
		print $cgi->redirect(%h);
	    }
	    else
	      {
		if ($cgi->param('unread') eq 'catchup')
		  {
		    $dbh->do('UPDATE users SET latestcommentread=NOW()'
			     .' WHERE (id='.$dbh->quote($userinfo->{'id'}).')');
		  }
		my (%h);
		$h{-cookie} = $cookie if ($cookie);
		print $cgi->header(%h);
		print '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "DTD/xhtml1-transitional.dtd">';
		my ($tree) = 
		  Flutterby::HTML::LoadHTMLFileAsTree($configuration->{-htmlpath}.'nounreadmessages.html');
		my ($out);
		$out = new Flutterby::Output::HTMLProcessed
		  (
		  );

		$out->output($tree);
	      }
	    $dbh->disconnect();
	    return;
	  }
	else
	  {
	    $userinfo = undef;
	  }
	
      }
    if (defined($userinfo)
	&& 
	(!defined($cgi->param('_comment'))
	 || defined($userinfo->{'id'})))
      {
	if (defined($cgi->param('_comment')))
	  {
	    if (defined($cgi->param('_comment_id')))
	    {
		my ($sql, $row, $sth);
		my ($terms);
		my ($texttype);
		$texttype = $cgi->param('_texttype');
		$texttype = '1' unless defined ($texttype);
		$terms = ' AND author_id='.$dbh->quote($userinfo->{'id'});

		Flutterby::DBUtil::escapeFieldsToEntities($cgi, '_text');
		$sql = 'UPDATE ARTICLES SET updated=NOW(), text='
		    .$dbh->quote($cgi->param('_text'))
			.', texttype='
			    .$dbh->quote($texttype)
				.' WHERE id='
				    .$dbh->quote($cgi->param('_comment_id'))
					.$terms;
		$dbh->do($sql) or die "$sql\n".$dbh->errstr;
	    }
	    else
	    {
		my ($sql);

		my ($prevtitle, $prevtext, $prevtexttype, $sth, $found);
		$sql = 'SELECT articles.title, articles.text, articles.texttype '
		    .'FROM weblogcomments, articles WHERE '
		    .'weblogcomments.article_id = articles.id '
		    ."AND articles.author_id='$userinfo->{'id'}' "
		    .'AND weblogcomments.entry_id='.$dbh->quote($cgi->param('id'));
		$sth = $dbh->prepare($sql)
		    || die $dbh->errstr."\n$sql\n";
		$sth->execute() 
		    || die $sth->errstr."\n$sql\n";
		while (($prevtitle, $prevtext, $prevtexttype) = $sth->fetchrow_array)
		{
		    if ($prevtitle eq $cgi->param('_title')
			&& $prevtext eq $cgi->param('_text')
			&& $prevtexttype eq $cgi->param('_texttype'))
		    {
			$found = 1;
		    }
		}

		if (!$found)
		{
		    my ($id) = $dbh->selectrow_array("SELECT nextval('articles_id_seq')");
		    Flutterby::DBUtil::escapeFieldsToEntities($cgi, '_text');

		    $sql = 'INSERT INTO articles (id, author_id, trackrevisions, title, text,texttype) VALUES ('
			."$id, $userinfo->{'id'}, 'true', "
			.$dbh->quote($cgi->param('_title')).','
			.$dbh->quote($cgi->param('_text')).','
			.$dbh->quote($cgi->param('_texttype')).')';
		    $dbh->do($sql) or die $dbh->errstr;
		    $sql = 'INSERT INTO weblogcomments(entry_id, article_id) '
			.'VALUES ('.$dbh->quote($cgi->param('id'))
			.", $id )";
		    
		    $dbh->do($sql) or die $dbh->errstr;
		    $dbh->commit();
		}
	    }
	}
    
	my ($query,$limit);
	$limit = '';
	$query = join(' OR ',
		      map
		      {
			'blogentries.id='.$dbh->quote($_);
		      } (split (/\,/,$cgi->param('entry_id'))))
	  if (defined($cgi->param('entry_id')));
	$query = join(' OR ',
		      map
		      {
			'blogentries.id='.$dbh->quote($_);
		      } (split (/\,/,$cgi->param('id'))))
	  if (defined($cgi->param('id')));
	if (defined($cgi->param('fromdate'))
	   || defined($cgi->param('todate')))
	  {
	    my ($f,$t);
	    $query .= 'blogentries.entered >= '.$dbh->quote($cgi->param('fromdate'))
	      if (defined($cgi->param('fromdate')));
	    $query .= ' or ' if (defined($cgi->param('fromdate'))
				      && defined($cgi->param('todate')));
	    $query .= 'blogentries.entered <= '.$dbh->quote($cgi->param('todate'))
	      if (defined($cgi->param('todate')));
	  }

	unless (defined($query))
	  {
	    my ($maxid) = $dbh->selectrow_array("SELECT MAX(id) FROM blogentries");
	    $query = 'blogentries.id='.int(rand($maxid));
	  }

	my ($tree) =
	  Flutterby::HTML::LoadHTMLFileAsTree($configuration->{-htmlpath}.'viewentry.html');
	my ($out, $formatters,$blogcommentsorder);
	$blogcommentsorder = '';
	if (defined($cgi->param('desc')))
	{
	    $blogcommentsorder = 'DESC'
		if ($cgi->param('desc') ne '0');
	}
	else
	{
	    $blogcommentsorder = 'DESC'
		if ($userinfo->{'showcommentsreversed'});
	}

	$variables->{'blogcommentsorder'} = $blogcommentsorder;
	$variables->{'blogcommentsdesc'} = $blogcommentsorder eq 'DESC' ? '0' : '1';
	$variables->{'blogcommentslabel'} = $blogcommentsorder eq 'DESC' ? 'descending' : 'ascending';
	$variables->{'userinfo_id'} = $dbh->quote($userinfo->{'id'});
	$variables->{'userinfo_entered'} = $dbh->quote($userinfo->{'entered'});
	$variables->{'userinfo_editblogentries'} = $dbh->quote($userinfo->{'editblogentries'});
	$variables->{'queryterms'} = $query;
	$variables->{'limitterms'} = $limit;
	$variables->{'textentryrows'} = $userinfo->{'textentryrows'} || 16;
	$variables->{'textentrycols'} = $userinfo->{'textentrycols'} || 80;
	$variables->{'addblogentries'} = $userinfo->{'addblogentries'} || '0';

	$formatters =
	  {
	   1 => new Flutterby::Parse::Text,
	   2 => new Flutterby::Parse::HTML,
	   'escapehtml' => new Flutterby::Parse::String,
	  };
	my (%h,@blogentries,@allowcomments, $lastmodified);
	$lastmodified = LoadEntriesToArray($dbh,\@blogentries,$formatters,$variables);
	LoadAllowCommentsArray($dbh, \@allowcomments, $variables, $blogentries[0]);

	$h{-cookie} = $cookie if ($cookie);
	$h{-Last_Modified} = $lastmodified if ($lastmodified);
	print $cgi->header(%h);
	print '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "DTD/xhtml1-transitional.dtd">';

	unless (defined($cgi->request_method()) && $cgi->request_method() eq 'HEAD')
	  {
	    $variables->{'blogentries'} = \@blogentries;
	    $variables->{'allowcomments'} = \@allowcomments;

	    $out = new Flutterby::Output::HTMLProcessed
	      (
	       -dbh => $dbh,
	       -variables => $variables,
	       -textconverters => $formatters,
	       -cgi => new CGI('id='.$cgi->param('id')),
	      );
	    $out->output($tree);
	  }
      }
    else
      {
	my (%h);
	$h{-cookie} = $cookie if ($cookie);
	print $cgi->header(%h);
	print '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0 Transitional //EN">';
	Flutterby::Users::PrintLoginScreen($configuration,
					   $cgi, $dbh,
					   '/archives/viewentry.cgi',
					   $loginerror);
      }
  }
my $dbh = DBI->connect($configuration->{-database},
			$configuration->{-databaseuser},
			$configuration->{-databasepass})
      or die DBI::errstr;
$dbh->{AutoCommit} = 1;

main($dbh);
$dbh->disconnect;
