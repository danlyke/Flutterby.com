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
use HTML::Entities;

sub main
  {
    my ($cgi, $dbh,$userinfo);
    $dbh = DBI->connect($configuration->{-database},
			$configuration->{-databaseuser},
			$configuration->{-databasepass})
      or die $DBI::errstr;
	$dbh->{AutoCommit} = 1;
    $cgi = new CGI;
    $userinfo = Flutterby::Users::CheckLogin($cgi,$dbh);

    my $tree = Flutterby::HTML::LoadHTMLFileAsTree($configuration->{-htmlpath}.'mapit.html');


    my @places;
    my $location;

    if (defined($cgi->param('pos')))
    {
	$location = $cgi->param('pos');
	my ($lat,$lon) = split(/,/, $cgi->param('pos'));

	push @places, '<a href="http://mapper.acme.com/?lat='
	    .HTML::Entities::encode($lat)
		.'&long='
		    .HTML::Entities::encode($lon)
			.'">mapper.acme.com</a>';
    }
    if (defined($cgi->param('addr')))
    {
	$location = $cgi->param('addr');
	my ($addr, $city, $country) = split /\s*\/\s*/, $cgi->param('addr');

	if (!defined($city) || $city eq '')
	{
	    if ($cgi->param('addr') =~ /^\s*(.*?)\,\s*(.*?)\s*$/)
	    {
		$addr = $1;
		$city = $2;
	    }
	}

	$country = 'us' if (!defined($country)
			    || $country =~ /^\s*(|united states|us|u.s.|usa|u.s.a.)\s*$/i);
	$country = 'ca' if ($country =~ /^\s*(ca|canada)w*$/i);

	$addr = $1 if ($addr =~ /^\s*(.*?)\s*$/);
	$city = $1 if ($city =~ /^\s*(.*?)\s*$/);
	$country = $1 if ($country =~ /^\s*(.*?)\s*$/);


	if ($country eq 'ca')
	{
	}
	else
	{
	    push @places, '<a href="http://maps.yahoo.com/maps_result?addr='
		.HTML::Entities::encode($addr)
		    .'&csz='
			.HTML::Entities::encode($city)
			    .'&country='
				.HTML::Entities::encode($country)
				    .'&new=1&name=&qty=">Yahoo Maps</a>';
	}

	push @places, '<a href="http://maps.google.com/maps?oi=map&q='
	    .HTML::Entities::encode("$addr, $city")
		.'">Google Maps</a>';

	if ($city =~ /^\s*(.*?)\,\s*(.+?)\s*$/)
	{
	    push @places, '<a href="http://www.mapquest.com/maps/map.adp?country='
		.HTML::Entities::encode(uc($country))
		    .'&address='
			.HTML::Entities::encode($addr)
			    .'&city='
				.HTML::Entities::encode($1)
				    .'&state='
					.HTML::Entities::encode($2)
					    .'">MapQuest</a>'
	}

	push @places, '<a href="http://mapper.acme.com/find.cgi?q='
	    .HTML::Entities::encode("$addr, $city")
		.'">mapper.acme.com</a>';
    }

    my ($variables);
    $variables = Flutterby::Users::GetWeblogInfo($cgi, $dbh);
    $variables->{'fcmsweblog_id'} = Flutterby::Users::GetWeblogID($cgi->url(), $dbh);
    $variables->{'userinfo_id'} = $dbh->quote($userinfo->{'id'});
    $variables->{'maplinks'} = join("\n / \n", @places);
    $variables->{'location'} = $location;

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




