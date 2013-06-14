#!/usr/bin/perl -w
use strict;
use CGI;
use DBI;
use URI::Escape;
use lib 'flutterby_cms';
use vars qw($configuration);
use Flutterby::Config;
$configuration ||= Flutterby::Config::load();


my $dbh;

$dbh = DBI->connect($configuration->{-database},
		    $configuration->{-databaseuser},
		    $configuration->{-databasepass})
    or die "DBH: $dbh\nDatabase: $configuration->{-database}\n"
    ."User: $configuration->{-databaseuser}\n"
    ."Password: $configuration->{-databasepass}\n"
    ."DBI Error: ".$DBI::errstr."\ndollarbang: $!\n";
	$dbh->{AutoCommit} = 1;
my $cgi = new CGI;

if (defined($cgi->param('target'))
       && defined($cgi->param('ticket'))
       && defined($cgi->param('lid_url')))
{
    my $url = $cgi->param('lid_url');
    my $target = $cgi->param('target');
    $target =~ s/\?.*$//;
    print STDERR "Redir to $url\n";
    print $cgi->redirect($url
			 .'?target='.uri_escape($target)
			 .'&ticket='.uri_escape($cgi->param('ticket'))
			 .'&action=sso-approve&credtype=gpg%20--clearsign')
}
