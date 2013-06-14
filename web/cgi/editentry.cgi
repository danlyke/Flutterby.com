#!/usr/bin/perl -w
use strict;
use CGI;
#use CGI::Carp qw(fatalsToBrowser);
use Data::Dumper;
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
use Flutterby::Parse::FullyEscapedString;
use Flutterby::Users;
use Flutterby::Tree::Find;
use Flutterby::DBUtil;

sub LoadTopicsToArray
{
    my ($dbh, $array ) = @_;

    my ($sql, $sth, $row);

    $sql = 'SELECT topic,id AS topic_id FROM articletopics'
	.' ORDER BY lower(topic)';

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
	    'edithtml' => new Flutterby::Parse::FullyEscapedString,
	};

    my ($categories) = LoadCategories($dbh);
    $cgi = new CGI;

    my ($variables);
    $variables = Flutterby::Users::GetWeblogInfo($cgi, $dbh);
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
	    
	    my $primary_url = $cgi->param('_primary_url');
	    my $enclosure_url = $cgi->param('_enclosure_url');
	    $primary_url = '' unless defined($primary_url);
	    $enclosure_url = '' unless defined($enclosure_url);
	    $sql = 'UPDATE weblogentries SET primary_url='
		.$dbh->quote($primary_url)
		    .', enclosure_url='
		.$dbh->quote($enclosure_url)
		    .'WHERE id='.$dbh->quote($cgi->param('_weblogentry_id'));
	    $dbh->do($sql)
		|| die $dbh->errstr."\n$sql\n";
	    
	    
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
		    .'(SELECT id FROM articletopics WHERE lower(topic)=lower('
			.$dbh->quote($cgi->param('_addnewtopic'))
			    .')),'.$cgi->param('_article_id').')';
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
		     'enclosure_url',
		     'deleted')
	    {
            $h{$_} = $dbh->quote($cgi->param("_$_"))
                if (defined($cgi->param("_$_")));
	    }
	    my ($articleid) =
		$dbh->selectrow_array("SELECT nextval('articles_id_seq')");
	    my $delay = 0;
	    $delay = $cgi->param('_publishdelay')
		if (defined($cgi->param('_publishdelay'))
		    && $cgi->param('_publishdelay') =~ /^\d+(\.\d+)$/);

	    $sql = 'INSERT INTO articles(id, trackrevisions, title, text,'
		."texttype, author_id, entered) VALUES ($articleid, false,"
		    .$dbh->quote($cgi->param('_title')).','
			.$dbh->quote($cgi->param('_text')).','
			    .$dbh->quote($cgi->param('_texttype'))
				.",$userinfo->{'id'}, NOW() + '$delay day'::interval )";
	    $dbh->do($sql) || die "$sql\n".$dbh->errstr;
	    my ($id) =
		$dbh->selectrow_array("SELECT nextval('weblogentries_id_seq')");
	    
	    my $primary_url = $cgi->param('_primary_url');
	    my $enclosure_url = $cgi->param('_enclosure_url');
	    $primary_url = '' unless defined($primary_url);
	    $enclosure_url = '' unless defined($enclosure_url);
	    $cgi->param('id' => $id, '_id' => $id);
	    $sql = "INSERT INTO weblogentries (id,article_id, "
		."primary_url,enclosure_url) VALUES ($id, $articleid,"
		    .$dbh->quote($primary_url)
			.','.$dbh->quote($enclosure_url)
			.')';
	    $dbh->do($sql) || die "$sql\n".$dbh->errstr;
	    
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
			if ($text =~ /(^|[^a-zA-Z0-9])$keyword(\$|[^a-zA-Z0-9])/i);
		    $categories{$categories->{$category}->{-id}} = 1	
			if (defined($subject) 
			    && $subject =~ /(^|[^a-zA-Z0-9])$keyword(\$|[^a-zA-Z0-9])/i);
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
    
	if (defined($cgi->param('_trackback')))
	{
	    my ($parser);
	    print STDERR "TRKBK: Sending trackback\n";
	    $parser = $textconverters->{$cgi->param('_texttype')};
	    if (defined($parser))
	    {
		print STDERR "TRKBK: Found parser\n";
		my $tree = $parser->parse($cgi->param('_text'));
		if (defined($tree))
		{
		    print STDERR "TRKBK: Parsed '".
			$cgi->param('_text')."'\n";
		    my (@links);
		    @links = Flutterby::Tree::Find::node($tree, 'a');
		    
		    use LWP::UserAgent;
		    my ($link);
		    my ($ua);
		    $ua = new LWP::UserAgent(agent 
					     => 'FlutterbyTrackbacker/0.01 (http://www.flutterby.net)');
		    
		    foreach $link (@links)
		    {
			if (defined($link->[1]->[0]->{href}))
			{
			    print STDERR "TRKBK: checking $link->[1]->[0]->{href}\n";
			    my ($response);
			    $response = $ua->get($link->[1]->[0]->{href});
			    if ($response->is_success)
			    {
				print STDERR "TRKBK: got URL\n";
				my ($t, $p);
				$p = new Flutterby::Parse::HTML(-parsecommentbody=>1,
								-allowalltags=>1);
				$t = $p->parse($response->content);
				if (defined($t))
				{
				    print STDERR "TRKBK: parsed content\n";
				    my (@rdfelements,$element);
				    @rdfelements = Flutterby::Tree::Find::node($t, 'rdf:RDF');
				    
				    foreach $element (@rdfelements)
				    {
					print STDERR "TRKBK: checking element $element\n";

					if (defined($element->[1]->[0]->{'xmlns:trackback'}))
					{
					    print STDERR "TRKBK: Found element $element->[1]->[0]->{'xmlns:trackback'}\n";
					    my ($ping);
					    $ping = Flutterby::Tree::Find::node($element, 'rdf:Description');
					    if (defined($ping) && $ping->[1]->[0]->{'trackback:ping'})
					    {
						print STDERR "TRKBK: Pinging post at $element->[1]->[0]->{'trackback:ping'}\n";
						print STDERR "TRKBK: Dumper start\n";
						print STDERR Dumper($ping);
						print STDERR "TRKBK: Dumper end\n";
						$response = $ua->post($ping->[1]->[0]->{'trackback:ping'},
								      'title' => $cgi->param('_title'),
								      'excerpt' => $cgi->param('_trackbackexcerpt'),
								      'blog_name' => $variables->{'fcmsweblog_title'},
								      'url' => 'http://www.flutterby.com/archives/comments/'
								      .$cgi->param('id').'.html');
					    }
					}
				    }
				}
			    }
			}
		    }
		}
	    }
	}
	my ($tree) = 
	  Flutterby::HTML::LoadHTMLFileAsTree($configuration->{-htmlpath}.'editentry.html');
    
	my ($query);
	$query = join(' OR ',
		      map
		      {
			'blogentries.id='.$dbh->quote($_);
		      } (split (/\,/,$cgi->param('_weblogentry_id'))))
	  if (defined($cgi->param('_weblogentry_id')));
	$query = join(' OR ',
		      map
		      {
			'blogentries.id='.$dbh->quote($_);
		      } (split (/\,/,$cgi->param('id'))))
	  if (defined($cgi->param('id')));


	my (@topicselectlist);
	LoadTopicsToArray($dbh,\@topicselectlist);
	$variables->{'topicselectlist'} = \@topicselectlist;
	$variables->{'userinfo_id'} = $dbh->quote($userinfo->{'id'});
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
					   './editentry.cgi',
					   $loginerror);
    }
    $dbh->disconnect;
}
&main;
