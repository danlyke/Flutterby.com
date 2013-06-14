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
use Flutterby::Util;
use Flutterby::DBUtil;

my ($validphotodirs) =
{
    'dssrt0000' => 1,
};

sub maineditphoto
{
    my ($cgi, $dbh,$userinfo,$loginerror,$continue);
    $dbh = DBI->connect($configuration->{-database},
			$configuration->{-databaseuser},
			$configuration->{-databasepass})
      or die DBI::errstr;
	$dbh->{AutoCommit} = 1;
	
    $cgi = new CGI;

    ($userinfo,$loginerror) = Flutterby::Users::CheckLogin($cgi,$dbh);
    if (defined($userinfo) && defined($userinfo->{'id'}))
    {
	my $ufh;
	if (defined($cgi->param('_uploadedphoto'))
	    && defined($ufh = $cgi->upload('_uploadedphoto')))
	{
	    my ($dir);
	    $dir = 'upld0000';
	    $dir = $cgi->param('dir')
		if (defined($cgi->param('dir'))
		    && defined($validphotodirs->{$cgi->param('dir')}));
	    my ($uploadedphoto, $ufh,$t,$l, $basename, $sql);
	    $ufh = $cgi->param('_uploadedphoto');
	    my ($year,$month,$day, $time, $resh, $resv, @techdetails);

	    my ($photoid) =
		$dbh->selectrow_array("SELECT nextval('photos_id_seq')");
	    
	    $basename = sprintf('img%6.6d', $photoid);
	    $uploadedphoto = "/home/danlyke/websites/flutterby.com/public_html/images/$dir/$basename.jpg";
	    
	    open O, ">$uploadedphoto"
		|| die "Unable to open output file $uploadedphoto\n";
	    
	    while (read($ufh, $t, 1024 * 32) > 0)
	    {
		print O $t;
	    }
	    close O;
	    $t = undef;
	    
	    if (open(JPEGINFO, "/usr/bin/jhead $uploadedphoto|"))
	    {
		while (<JPEGINFO>)
		{
		    if (/^Resolution +\: +(\d+) *x *(\d+)/i)
		    {
			$resh = $1;
			$resv = $2;
		    }
		    elsif (/^Date\/Time\s+\:\s+(\d+)\:(\d+)\:(\d+)\s+(\d+\:\d+\:\d+)/)
		    {
			$year = $1;
			$month = $2;
			$day = $3;
			$time = $4;
		    }
		    elsif (/^File /)
		    {
		    }
		    elsif (/^Jpeg /)
		    {
		    }
		    elsif (/^(\w.*?)\s*\:\s(.*)$/)
		    {
			push @techdetails, "$1 : $2";
		    }
		}
		close JPEGINFO;
	    }
	    elsif (open(JPEGINFO, "/usr/bin/mogrify -verbose $uploadedphoto|"))
	    {
		while (<JPEGINFO>)
		{
		    if (/(\d+)x(\d+)/)
		    {
			$resh = $1;
			$resv = $2;
		    }
		}
		close JPEGINFO;
	    }
	    else
	    {
		die "Unable to open $uploadedphoto";
	    }
	    die "No res found" unless defined($resh);
	    my ($articleid) =
		$dbh->selectrow_array("SELECT nextval('articles_id_seq')");
	    my ($peopleid) =
		$dbh->selectrow_array("SELECT id FROM people WHERE $userinfo->{'id'} = user_id");
	    if (!defined($peopleid))
	    {
		($peopleid) =
		    $dbh->selectrow_array("SELECT nextval('people_id_seq')");
		
		if (defined($peopleid))
		{
		    $sql = 'INSERT INTO people(id, user_id, name) VALUES ('
			."$peopleid, $userinfo->{'id'},"
			    .$dbh->quote($userinfo->{'name'})
				.")";
		    $dbh->do($sql)
			|| die $dbh->errstr."\n$sql";
		}
		else
		{
		    # If we don't have it yet, then make a last-ditch
		    # effort to get it again in case we've got some
		    # sort of concurrency issue going on.
		    
		    ($peopleid) =
			$dbh->selectrow_array("SELECT id FROM people WHERE $userinfo->{'id'} = user_id");
		}
		
	    }
	    
	  Flutterby::DBUtil::escapeFieldsToEntities($cgi, '_text','_title');
	    
	    my ($articletitle, $articletext, $articletexttype);
	    $articletitle = $cgi->param('_title');
	    $articletitle = '' unless defined($articletitle);
	    $articletext = $cgi->param('_text');
	    $articletext = '' unless defined($articletext);
	    $articletexttype = $cgi->param('_texttype');
	    $articletexttype = '1' unless defined($articletexttype);
	    
	    
	    $sql = 'INSERT INTO articles(id, trackrevisions, title, text,'
		    ."texttype, author_id) VALUES ($articleid, false,"
			.$dbh->quote($articletitle).','
			    .$dbh->quote($articletext).','
				.$dbh->quote($articletexttype)
				    .",$userinfo->{'id'} )";
	    $dbh->do($sql)
		|| die $dbh->errstr."\n----\n$sql\n";
	    
	    $sql = "INSERT INTO photos(id, article_id, directory, name, taken, tech_notes, photographer_id) VALUES ($photoid, $articleid, '$dir', '$basename',"
		.(defined($year) 
		  ? $dbh->quote(sprintf("%4.4d-%2.2d-%2.2d $time",
					$year, $month, $day))
		  : 'NOW()')
		    .','
			.$dbh->quote(join(" / ", @techdetails))
			    .",$peopleid )";
	    
		
	    $dbh->do($sql)
		|| die $dbh->errstr."\n----\n$sql\n";
	    
	    my (%sizes, $wantedv, $extension);
	    %sizes = (
		      128 => 'sm',
		      512 => 'md',
		      768 => 'lg');
	    
	    while (($wantedv, $extension) = each (%sizes))
	    {
		if ($wantedv / $resv < .5)
		{
		    my ($ratio, $name);
		    $name = "$basename.$extension.jpg";
		    $ratio = int(100 * $wantedv / $resv);
		    system("convert $uploadedphoto -geometry $ratio\% /home/danlyke/websites/flutterby.com/public_html/images/$dir/$name");
		    my ($x, $y);
		    
		    $x = int($resh * $ratio / 100);
		    $y = int($resv * $ratio / 100);
		    $sql = "INSERT INTO photosizes(photo_id, width, height, filename) VALUES ($photoid, $x, $y, '$name')";
		    $dbh->do($sql)
			|| die $dbh->errstr."\n----\n$sql\n";
		}
	    }
	    $sql = "INSERT INTO photosizes(photo_id, width, height, filename) VALUES ($photoid, $resh, $resv, '$basename.jpg')";
	    $dbh->do($sql)
		|| die $dbh->errstr."\n----\n$sql\n";
	    $dbh->commit();
	    $cgi->param('id' => $photoid);
	    $cgi->param('size' => '0');
	    $cgi->param('_uploadedphoto'=>undef);
	}
	elsif (defined($cgi->param('_update')))
	{
	    print $cgi->header;
	    my ($terms);
	  Flutterby::DBUtil::updateMultipleRecords($dbh,$cgi,'photos','id',
						   [
						    'taken',
						    'model_release',
						    'tech_notes',
						    'location',
						    'camera_position_lattitude',
						    'camera_position_longitude',
						    'camera_position_acuracy',
						    'subject_position_lattitude',
						    'subject_position_longitude',
						    'subject_position_acuracy',
						    ],
						   $terms);
	    $terms = ' author_id='.$dbh->quote($userinfo->{'id'})
		unless ($userinfo->{'editphotoentries'});
	  Flutterby::DBUtil::updateMultipleRecords($dbh,$cgi,'articles','_article_id',
						   {
						       '_title' => 'title',
						       '_text', => 'text',
						       '_article_id' => 'id',
						   },
						   $terms,
						   '_text', '_title');
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
				    '1'))
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
	  Flutterby::HTML::LoadHTMLFileAsTree($configuration->{-htmlpath}.'editphoto.html');
	my ($variables);
	$variables = Flutterby::Users::GetWeblogInfo($cgi, $dbh);
	$variables->{'userinfo_id'} = $dbh->quote($userinfo->{'id'});
	$variables->{'userinfo_editphotoentries'} = $dbh->quote($userinfo->{'editphotoentries'});
	$variables->{'queryterms'} = $query;
	$variables->{'limitterms'} = $limit;
	$variables->{'sizeimagetoshow'} = $imagetoshow;
	$variables->{'textentryrows'} = $userinfo->{'textentryrows'} || 16;
	$variables->{'textentrycols'} = $userinfo->{'textentrycols'} || 80;

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
	   -cgi =>
	   {
	    './editphoto.cgi' =>
	    {
	     -cgi => $cgi,
	     -action => 
	     Flutterby::Util::buildGETURL('./editphoto.cgi',$cgi),
	    }
	   }
	  );
	$out->output($tree);
      }
    else
      {
	Flutterby::Users::PrintLoginScreen($configuration,
					   $cgi, 
					   $dbh, 
					   './editphoto.cgi',
					   $loginerror);
      }
    $dbh->disconnect;
  }
&maineditphoto;
