#!/usr/bin/perl -w
use strict;
use CGI;
use DBI;
use lib 'flutterby_cms';
use vars qw($configuration);
use Flutterby::Config;
$configuration ||= Flutterby::Config::load();
use Flutterby::HTML;
use Flutterby::Output::HTMLProcessed;
use vars qw($queryCache);
use lib 'flutterby_cms';
$queryCache ||= {};

sub GetWordList($@)
{
    my ($dbh, $titles, @wordlist) = @_;
    my (%wordlist,$word,$w);
    
    my ($a,$rec,$sql,$sth);
my ($begin) = time();
    $sql = 'SELECT urls.url,searchurlwords.pos,urls.title,searchwords.word FROM searchwords, searchurlwords,urls WHERE searchurlwords.word_id=searchwords.id AND searchurlwords.url_id=urls.id AND searchwords.word IN ('
      . join(', ',
	     map { $dbh->quote(uc($_)); } @wordlist)
	.')';
    $sth = $dbh->prepare($sql);
    $sth->execute();
    while ($rec = $sth->fetchrow_arrayref())
    {
	$wordlist{$rec->[3]} = {} unless $wordlist{$rec->[3]};
	$wordlist{$rec->[3]}->{$rec->[0]} = [] unless $wordlist{$rec->[3]}->{$rec->[0]};
	$titles->{$rec->[0]} = $rec->[2];
	push @{$wordlist{$rec->[3]}->{$rec->[0]}}, $rec->[1];
    }
    return \%wordlist;
}

sub MatchPhrase($$$)
 {
    my ($wordlist,$docsfound, $phrase) = @_;
    my ($w,$word, @phrase);
    ($w, @phrase) = split(/[\W_]+/,$phrase);
    $word = uc($w);
    my ($doclist, $doc);

    $doclist = $wordlist->{$word};
    foreach $doc (keys %$doclist)
    {
	my (@pos);
	@pos = @{$doclist->{$doc}};

	foreach $w (@phrase) 
	  {
	    $word = uc($w);
	    my (@newpos, $newpos, $pos);
	    $newpos = $wordlist->{$word}->{$doc};
	    foreach $pos (@pos)
	      {
		foreach (@$newpos)
		  {
		    push @newpos, $_ if ($_ = $pos + 1);
		  }
	      }
	    @pos = @newpos;
	  }
	if ($#pos >= 0)
	{
	    $docsfound->{$doc} = 0 unless defined($docsfound->{$doc});
	    $docsfound->{$doc}+= $#pos + 1;
	}
    }
}


sub main()
{
    my ($cgi) = new CGI;
    my ($search);
    $search = $cgi->param('q');
    $search = $cgi->param('search') unless defined($search);

    $search = undef if ($search =~ /http.*http/);
    my ($start, $perscreen, $end, $results, $i);
    
    print $cgi->header();
    print '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "DTD/xhtml1-transitional.dtd">';
    my ($cacheTime) = time() - 60 * 20;
    foreach (keys %$queryCache)
    {
	delete $queryCache->{$_}
	unless ($queryCache->{$_}->{-time} > $cacheTime);
    }
    if (defined($search))
    {
	unless (defined($queryCache->{$search}))
	{
	    my ($dbh);
	
	    $dbh = DBI->connect($configuration->{-database},
				$configuration->{-databaseuser},
				$configuration->{-databasepass})
		or die $DBI::errstr;
	$dbh->{AutoCommit} = 1;
	    my (@words,@require,@exclude,@rank);
	    @words = grep { $_ ne '' } split(/[\W_]+/,$search);
	    my ($parseSearch);
	    $parseSearch = $search;
	    while ($parseSearch =~ s/^\s*([\+\-]?)(\"(.*?)\"|\'(.*?)\'|(\w+))//)
	    {
		my ($incexc,$term);
		$incexc = $1;
		$term = $3 if ($3);
		$term = $4 if ($4);
		$term = $5 if ($5);
		if ($term)
		{
		    if ($incexc)
		    {
			if ($incexc eq '+')
			{
			    push @require, $term;
			}
			else
			{
			    push @exclude, $term;
			}
		    }
		    else
		    {
			push @rank, $term;
		    }
		}
	    }
	    my (%requireddocs, %excludeddocs, %rankdocs);
	    
	    my ($words,$phrase,%titles);
	    $words = GetWordList($dbh,\%titles,@words);
	    
	    
	    foreach $phrase (@require)
	    {
		MatchPhrase($words,\%requireddocs,$phrase);
	    }
	    foreach $phrase (@exclude)
	    {
		MatchPhrase($words,\%excludeddocs,$phrase);
	    }
	    foreach $phrase (@rank)
	    {
		MatchPhrase($words,\%rankdocs,$phrase);
	    }
	
	    if ($#require >= 0)
	    {
		foreach (keys %requireddocs)
		{
		    $rankdocs{$_} = 1 unless defined($rankdocs{$_});
		}
		foreach (keys %rankdocs)
		{
		    if ($requireddocs{$_})
		    {
			$rankdocs{$_} += $requireddocs{$_};
		    }
		    else
		    {
			delete $rankdocs{$_};
		    }
		}
	    }
	    if ($#exclude >= 0)
	    {
		foreach (keys %excludeddocs)
		{
		    delete $rankdocs{$_}
		    if ($rankdocs{$_});
		}
	    }
	    my (@results);
	    @results = map 
	    { 
		{
		    'url' => $_,
		    'title' => $titles{$_},
		  'rank' => $rankdocs{$_}
		};
	    } (sort {$rankdocs{$b} <=> $rankdocs{$a}} keys %rankdocs);

	    $queryCache->{$search} = {-results => \@results, -time => time()};
	    $dbh->disconnect;
	}
	$results = $queryCache->{$search}->{-results};
    }

    $results = [];
    $results = $queryCache->{$search}->{-results}
          if (defined($search) 
	      && defined($queryCache->{$search})
	      && defined($queryCache->{$search}->{-results}));

    $start = 0;
    $start = $cgi->param('s') if defined($cgi->param('s'));
    $perscreen = 25;
    $perscreen = $cgi->param('n') if defined($cgi->param('n'));
    $end = $start + $perscreen;
    $end = $#$results + 1 if ($#$results <= $start + $perscreen);

    my (@outputresults);
    for ($i = $start; $i < $end; $i++)
    {
	push @outputresults, $results->[$i];
    }

    my ($begin);
    $begin = $start - $perscreen;
    $begin = 0 if ($begin < 0);
    
    my ($tree) = 
      Flutterby::HTML::LoadHTMLFileAsTree($configuration->{-htmlpath}.'search.html');
    my ($variables);
    $variables = Flutterby::Users::GetWeblogInfo($cgi, $dbh);
    $variables->{'searchresults'} => $#outputresults ? \@outputresults : '';
    $variables->{'prevresults'} => ($start > 0) ? [{}] : undef;
    $variables->{'nextresults'} => ($#$results >= $end) ? [{}] : undef;
    my ($out);
    $out = new Flutterby::Output::HTMLProcessed
      (
       -classcolortags => $configuration->{-classcolortags},
       -colorschemecgi => $cgi,
       -variables => $variables,
       -cgi =>
       {
	'./search.cgi' => new CGI({'s' => $start+$perscreen,
				   'n' => $perscreen,
				   'q' => $search}),
	'prev' =>
	{
	 -cgi => new CGI({'s' => $start-$perscreen,
			  'n' => $perscreen,
			  'q' => $search}),
	 -action => './search.cgi',
	},
	'next' =>
	{
	 -cgi => new CGI({'s' => $end, 'n' => $perscreen, 'q' => $search}),
	 -action => './search.cgi',
	},
       }
      );
    $out->output($tree);
  }

main();
