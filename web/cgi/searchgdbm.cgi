#!/usr/bin/perl -w
use strict;
use CGI;
use DB_File;
use lib 'flutterby_cms';
use vars qw($configuration);
use Flutterby::Config;
$configuration ||= Flutterby::Config::load();
use Flutterby::HTML;
use Flutterby::Output::HTMLProcessed;
use vars qw($queryCache);
$queryCache ||= {};


sub TieHash($)
  {
    my ($filename) = @_;
    my (%h);
    tie(%h, 'DB_File', 
	$filename, 
	O_RDONLY, 0644)
      || die "tie $filename $!\n";
    return \%h;
  }

my ($tableUrlsToId,$tableIdsToUrl,$tableWords);
$tableUrlsToId = TieHash('search_urlstoid.db')
  unless defined($tableUrlsToId);
$tableIdsToUrl = TieHash('search_idstourl.db')
  unless defined($tableIdsToUrl);
$tableWords = TieHash('search_words.db')
  unless defined($tableWords);;

sub GetWordList($@)
  {
    my ($titles, @wordlist) = @_;
    my (%wordlist,$word,$w);

    my ($begin) = time();

    foreach $w (@wordlist)
      {
	$word = uc($w);
	my (%h);
	if ($tableWords->{$word})
	  {
	    %h = unpack ('S*',$tableWords->{$word});
	  }
	foreach (keys %h)
	  {
	    my ($i,$url,$ntitle);
	    ($url,$ntitle) = split /\x01/, $tableIdsToUrl->{$_};
	    $wordlist{$word} = {} unless $wordlist{$word};
	    $wordlist{$word}->{$url} = []
	      unless $wordlist{$word}->{$url};

	    $titles->{$url} = $ntitle;

	    for ($i = 0; $i < 16; $i++)
	      {
		push @{$wordlist{$word}->{$url}}, $i
		  if ($h{$_} & (1 << $i));
	      }
	  }
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
		    push @newpos, ($_ % 16) if ($_ = (($pos + 1) % 16));
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
    my ($start, $perscreen, $end, $results, $i);
    print $cgi->header();
    print '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "DTD/xhtml1-transitional.dtd">';
    $search = $cgi->param('q');
    $search = $cgi->param('search') unless defined($search);
    
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
	    $words = GetWordList(\%titles,@words);
	    
	
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
    print STDERR "Checking required docs\n";
    

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
	    my (@results,$index,@a);
	    $index = 1;
	    @a = (sort {$rankdocs{$b} <=> $rankdocs{$a}} keys %rankdocs);
	    foreach (@a)
              {
		push @results,
		{
		  'totalresults' => $#a,
		  'resultnumber' => $index,
		  'url' => $_,
		  'title' => $titles{$_},
		  'rank' => $rankdocs{$_}
		};
		$index ++;
	      }
	    $queryCache->{$search} = {-results => \@results, -time => time()};
	  }
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

    print STDERR "Start is $start\n";
    my (@outputresults);
    for ($i = $start; $i < $end; $i++)
      {
	push @outputresults,$results->[$i];
      }

    my ($begin);
    $begin = $start - $perscreen;
    $begin = 0 if ($begin < 0);
    
    my ($tree) = 
      Flutterby::HTML::LoadHTMLFileAsTree($configuration->{-htmlpath}.'search.html');
    my ($variables);
    $variables = Flutterby::Users::GetWeblogInfo($cgi, $dbh);
    $variables->{'fcmsweblog_id'} => Flutterby::Users::GetWeblogID($cgi->url(), $dbh);
    $variables->{'searchresults'} => ($#outputresults >= 0) ? \@outputresults : undef;
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
	'./search.cgi' => new CGI({'s' => '0',
				   'n' => $perscreen,
				   'q' => $search}),
	'prev' =>
	{
	 -cgi => new CGI({'s' => ($start-$perscreen < 0) ? 0 : $start-$perscreen,
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
