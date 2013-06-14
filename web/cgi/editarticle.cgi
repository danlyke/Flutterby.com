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

sub LoadTopicsToArray
{
    my ($dbh, $array ) = @_;

    my ($sql, $sth, $row);

    $sql = 'SELECT topic,id AS topic_id FROM articletopics'
	.' ORDER BY UPPER(topic)';

    $sth = $dbh->prepare($sql) 
      || die "$sql\n".$dbh->errstr;
    $sth->execute
      || die "$sql\n".$sth->errstr;
    while ($row = $sth->fetchrow_hashref)
    {
	push @$array, $row;
    }
}


sub LoadCategories($)
{
    my ($dbh) = @_;
    my ($sql, $sth,$id,$topic,$text,$categories);
    $categories = {};
    $sql = 'SELECT articletopics.id,topic,text FROM articletopics, articletopicterms WHERE articletopics.id=articletopicterms.topic_id';
    $sth = $dbh->prepare($sql) or die $dbh->errstr;
    $sth->execute or die $sth->errstr;
    while (($id,$topic,$text) = $sth->fetchrow_array)
    {
	$categories->{$topic} = {-id=>$id,-terms=>[]} unless defined($categories->{$topic});
	push @{$categories->{$topic}->{-terms}},$text;
    }
    return $categories;
}


sub main
{
    my ($cgi, $dbh,$userinfo,$loginerror,$textconverters);
    $dbh = DBI->connect($configuration->{-database},
			$configuration->{-databaseuser},
			$configuration->{-databasepass})
	or die $DBI::errstr;
$dbh->{AutoCommit} = 1;
    $textconverters = 	   { 
	    1 => new Flutterby::Parse::Text,
	    2 => new Flutterby::Parse::HTML,
	    'escapehtml' => new Flutterby::Parse::String,
	};

    my ($categories) = LoadCategories($dbh);
    $cgi = new CGI;

    ($userinfo,$loginerror) = Flutterby::Users::CheckLogin($cgi,$dbh);

    if (defined($userinfo->{'id'}))
    {
	my ($terms);

	if ($cgi->param('_article_id'))
	{
	    my ($sql);
	    if ($cgi->param('_text'))
	    {
		my ($t) = $cgi->param('_text');
		$t =~ s/\r//g;
		$cgi->param('_text' => $t);
	    }
	    $terms = ' AND author_id='.$dbh->quote($userinfo->{'id'})
		unless ($userinfo->{'editblogentries'});

	    
	    Flutterby::DBUtil::escapeFieldsToEntities($cgi, '_text','_title');

	    $sql = "UPDATE articles SET "
		.join(',',
		      map 
		      {
			  "$_=".$dbh->quote($cgi->param('_'.$_));
		      }
		      ('text','texttype','title'))
		." WHERE id=".$dbh->quote($cgi->param('_article_id'))
		.$terms;
	    $dbh->do($sql)
		|| print $dbh->errstr."\n$sql\n";
	    

	    my (%h,@newtopics);
	    foreach ($cgi->param())
	    {
		$h{$1} = 1 if (/^_topic\.(\d+)$/);
		if (/^_newtopic(\d+)$/ && $cgi->param($_) ne '')
		{
		    push @newtopics, $cgi->param($_);
		    $cgi->param($_ => '');
		}
	    }
	    my ($sth,$row);
	    $sql = 'SELECT topic_id FROM articletopiclinks WHERE article_id='
		.$cgi->param('_article_id');
	    $sth = $dbh->prepare($sql)
		or die $sql."\n".$dbh->errstr;
	    $sth->execute or die $sth->errstr;
	    while ($row = $sth->fetchrow_arrayref)
	    {
			unless ($h{$row->[0]})
			{
				$dbh->do("DELETE FROM articletopiclinks WHERE topic_id=$row->[0] AND article_id="
						 .$cgi->param('_article_id'));
				$dbh->commit();
	    }
	    foreach (@newtopics)
	    {
		$sql = 
		    'INSERT INTO articletopiclinks (topic_id,article_id) VALUES ('
			.$_.','.$cgi->param('_article_id').')';
		unless ($dbh->do($sql))
		{
		    # most conceivable error here is "duplicate key",
		    # which we want to ignore.
		}
	    }
	    if ($cgi->param('_addnewtopic'))
	    {
		$sql = 'INSERT INTO articletopics (topic) VALUES ('
		    .$dbh->quote($cgi->param('_addnewtopic')).')';
		$dbh->do($sql)
		    || print STDERR "$sql\n".$dbh->errstr;
		$sql = 'INSERT INTO articletopiclinks(topic_id, article_id) VALUES ('
		    .'(SELECT id FROM articletopics WHERE topic='
			.$dbh->quote($cgi->param('_addnewtopic'))
			    .'),'.$cgi->param('_article_id').')';
		$dbh->do($sql)
		    || print STDERR "$sql\n".$dbh->errstr;
	    }
	}
	elsif (grep { /^_/ } $cgi->param)
	{
	    my ($sql);
	    my (%h);
	    $h{'author_id'} = $dbh->quote($userinfo->{'id'});

	    Flutterby::DBUtil::escapeFieldsToEntities($cgi, '_text','_title');
	    foreach ('text',
		     'texttype',
		     'subject',
		     'category',
		     'primary_url',
		     'deleted')
	    {
		$h{$_} = $dbh->quote($cgi->param("_$_"))
		    if (defined($cgi->param("_$_")));
	    }
	    foreach ('_title', '_text', '_texttype')
	    {
		print "<p><b>$_</b> undefined</p>\n"
		    unless defined($cgi->param($_));
	    }
	    my ($articleid) =
		$dbh->selectrow_array("SELECT nextval('articles_id_seq')");
	    $sql = 'INSERT INTO articles(id, trackrevisions, title, text,'
		."texttype, author_id) VALUES ($articleid, false,"
		.$dbh->quote($cgi->param('_title')).','
		.$dbh->quote($cgi->param('_text')).','
		.$dbh->quote($cgi->param('_texttype'))
		.",$userinfo->{'id'} )";
	    $dbh->do($sql) || die "$sql\n".$dbh->errstr;
	    
	    $cgi->param('id' => $articleid, '_article_id' => $articleid);

	    my ($text) = $cgi->param('_text');
	    my ($subject) = $cgi->param('_subject');
	    my ($category, %categories);
	    foreach $category (keys %$categories)
	    {
		my ($keywords);
		
		$keywords = $categories->{$category}->{-terms};
		foreach (@$keywords)
		{
		    $text =~ s/\s+/ /sg;
		    my ($keyword) = $_;
		    $categories{$categories->{$category}->{-id}} = 1
			if ($text =~ /(^|\W)$keyword(\$|\W)/i);
		    $categories{$categories->{$category}->{-id}} = 1	
			if (defined($subject) 
			    && $subject =~ /(^|\W)$keyword(\$|\W)/i);
		}
	    }
	    foreach $category (keys %categories)
	    {
		$sql = 'INSERT INTO articletopiclinks (topic_id,article_id) VALUES ('
		    .join(',',map {$dbh->quote($_)} ($category,$articleid))
			.')';
		$dbh->do($sql);
	    }
	}
	print STDERR "About to display editarticle.html\n";
	my ($tree) = 
	  Flutterby::HTML::LoadHTMLFileAsTree($configuration->{-htmlpath}.'editarticle.html');
	
	my ($query);
	$query = join(' OR ',
		      map
		      {
			'articles.id='.$dbh->quote($_);
		      } (split (/\,/,$cgi->param('_article_id'))))
	    if (defined($cgi->param('_article_id')));
	$query = join(' OR ',
		      map
		      {
			'articles.id='.$dbh->quote($_);
		      } (split (/\,/,$cgi->param('id'))))
	    if (defined($cgi->param('id')))
;	print STDERR "With query $query\n";
	my (@topicselectlist);
	LoadTopicsToArray($dbh,\@topicselectlist);
	my ($variables);
	$variables = Flutterby::Users::GetWeblogInfo($cgi, $dbh);
	$variables->{'topicselectlist'} = \@topicselectlist;
	$variables->{'userinfo_id'} = $dbh->quote($userinfo->{'id'});
	$variables->{'blogentrydbl_id'} = $cgi->param('id');
	$variables->{'userinfo_editblogentries'} = $dbh->quote($userinfo->{'editblogentries'});

	$variables->{'textentryrows'} = $userinfo->{'textentryrows'} || 16;
	$variables->{'textentrycols'} = $userinfo->{'textentrycols'} || 80;
	$variables->{'queryterms'} = $query;
	my ($out);
	$out = new Flutterby::Output::HTMLProcessed
	    (
	     -classcolortags => $configuration->{-classcolortags},
	     -colorschemecgi => $cgi,
	     -dbh => $dbh,
	     -variables => $variables,
	     -textconverters => $textconverters,
	     -cgi => $cgi
	     );
	$out->output($tree);
    }
    else
    {
        Flutterby::Users::PrintLoginScreen($configuration,
					   $cgi, 
					   $dbh, 
					   './editarticle.cgi',
					   $loginerror);
    }
    $dbh->disconnect;
}
&main;
