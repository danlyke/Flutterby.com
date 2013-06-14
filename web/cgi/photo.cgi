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
use Flutterby::Util;
use Flutterby::DBUtil;

sub main
  {
    my ($cgi, $dbh,$userinfo,$loginerror,$continue);
    $dbh = DBI->connect($configuration->{-database},
			$configuration->{-databaseuser},
			$configuration->{-databasepass})
      or die DBI::errstr;
	$dbh->{AutoCommit} = 1;
    $cgi = new CGI;

    ($userinfo,$loginerror) = Flutterby::Users::CheckLogin($cgi,$dbh);
    if (defined($userinfo)
	&& 
	(!defined($cgi->param('_update'))
	 || defined($userinfo->{'id'})))
      {
	if (defined($cgi->param('_update')))
	  {
	    my ($terms);
	    $terms = ' photographer_id='.$dbh->quote($userinfo->{'id'})
	      unless ($userinfo->{'editphotoentries'});
	    Flutterby::DBUtil::updateRecord($dbh,$cgi,'photos','id',
					    [
					     'taken',
					     'model_release',
					     'tech_notes',
					     'alt_text',
					     'description',
					    ],
					    $terms);
	  }
    
	my ($query,$limit);
	my ($imagetoshow);
	$imagetoshow = 1;
	if (defined($cgi->param('size')))
	  {
	    $imagetoshow = 
	      {
	       'sm' => 0,
	       'md' => 1,
	       'lg' => 2,
	       'hg' => 3,
	       'small' => 0,
	       'medium' => 1,
	       'large' => 2,
	       'huge' => 3,
	      }->{$cgi->param('size')};
	    $imagetoshow = $cgi->param('size') unless defined($imagetoshow);
	  }
	
	$limit = '';
	$query = join(' OR ',
		      map
		      {
			/^\d+$/ ? 'photos.id='.$dbh->quote($_)
			  : 
			    (/^\w+$/ ? 'photos.directory='.$dbh->quote($_) 
			     :
			     (/^(\w+)\/(\w+)$/ ? ('(photos.directory='.$dbh->quote($1)
						  .' AND photos.name='.$dbh->quote($2).')')
			      :
			      'false'))
		      } (split (/\,/,$cgi->param('id'))))
	  if (defined($cgi->param('id')));

	$query = "($query)".
	  (defined($cgi->param('fromdate')) ?
	    ' AND taken >= '.$dbh->quote($cgi->param('fromdate'))
	      :
	   '')
	    .(defined($cgi->param('fromdate')) ?
	    ' AND taken <= '.$dbh->quote($cgi->param('todate'))
	      :
	      '')
	      if (defined($cgi->param('fromdate')) || defined($cgi->param('todate')));
	$query = "($query) AND show_on_browse"
	  unless (defined($userinfo->{'id'}) && $userinfo->{'id'} == 1);

	my ($tree) =
	  Flutterby::HTML::LoadHTMLFileAsTree($configuration->{-htmlpath}.'photo.html');
	my ($variables);
	$variables = Flutterby::Users::GetWeblogInfo($cgi, $dbh);
	$variables->{'userinfo_id'} = $dbh->quote($userinfo->{'id'});
	$variables->{'userinfo_editphotoentries'} = $dbh->quote($userinfo->{'editphotoentries'});
	$variables->{'queryterms'} = $query;
	$variables->{'limitterms'} = $limit;
	$variables->{'sizeimagetoshow'} = $imagetoshow;
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
	   }
	  );
	$out->output($tree);
      }
    else
      {
	Flutterby::Users::PrintLoginScreen($configuration,
					   $cgi, 
					   $dbh,
					   './photo.cgi',
					   $loginerror);
      }
    $dbh->disconnect;
  }
&main;
