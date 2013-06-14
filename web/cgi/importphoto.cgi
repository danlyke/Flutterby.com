#!/usr/bin/perl -w
use strict;
use CGI qw(-debug );
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

my ($debug);
$debug = 1;


sub processcurrentfile($$$$$$$)
{
    my ($dbh, $userinfo, $dir,$currfile,$status,$rootprocessed,$alreadythere) = @_;
    my ($file, $ext, $width, $height, $sql);

    ($file, $ext) = ($1, $2) 
	if ($currfile->{'File name'} =~
	    /\/(\w+)(a\.jpg|\..*?jpg|\..*?thm)/i);
    ($width, $height) = ($1, $2)
	if ($currfile->{'Resolution'} =~ /(\d+) *x *(\d+)/);
    
    push @$status, "Got file $file\n<br />";
    push @$status, "Got $ext<br/>" if ($ext eq '.JPG');
    
    my ($imageid, $taken);
    
    if (defined($currfile->{'Date/Time'}))
    {
	$taken = $currfile->{'Date/Time'};
	$taken =~ s/^(\d+):(\d+):/$1-$2-/;
	$taken = $dbh->quote("$taken -0");
    }

    if (defined($rootprocessed->{$file}))
    {
	$imageid = $rootprocessed->{$file};
    }
    else
    {
	if (defined($alreadythere->{$file}))
	{
	    $imageid = $alreadythere->{$file};
	    $sql = "DELETE FROM photosizes WHERE photo_id=$imageid";
	    $dbh->do($sql)
		|| die "$sql\n".$dbh->errstr;
	}
	else
	{
	    my ($article_id);
	    $sql = "SELECT nextval('photos_id_seq')";
	    ($imageid) =
		$dbh->selectrow_array($sql)
		    || die "$sql\n".$dbh->errstr;
	    
	    ($article_id) = 
		$dbh->selectrow_array("SELECT nextval('articles_id_seq')");
	    $sql = 'INSERT INTO articles (id, author_id) VALUES ('
		."$article_id, $userinfo->{'id'})";
	    $dbh->do($sql) or die $dbh->errstr;
				    
	    $sql = 'INSERT INTO photos(id, photographer_id, article_id,directory, name) VALUES ('
		."$imageid, $userinfo->{'id'}, $article_id, '$dir', '$file' )";
	    push @$status, "$sql\n<br />";
				$dbh->do($sql)
				    || die "$sql\n".$dbh->errstr;
	}
	$rootprocessed->{$file} = $imageid;
    }
    if (defined($taken))
    {
	$sql = "UPDATE photos SET taken=$taken WHERE id=$imageid";
	push @$status, "$sql\n<br />";
	$dbh->do($sql)
	    || push @$status, "$sql\n".$dbh->errstr;
    }
    my (@techinfo);
    
    foreach (
	     'Camera model',
	     'Flash used',
	     'Focal length',
	     'CCD Width',
	     'Exposure time',
	     'Aperture',
	     'Focus Dist.',
	     'Metering Mode'
	     )
    {
	push @techinfo, "$_ : $currfile->{$_}"
	    if (defined($currfile->{$_}));
    }
    if ($#techinfo >= 0)
    {
	$sql = "UPDATE photos SET tech_notes="
	    .$dbh->quote(join(" / ", @techinfo))
		." WHERE id=$imageid";
	push @$status, "$sql\n<br />";
	$dbh->do($sql)
	    || die "$sql\n".$dbh->errstr;
    }
    $sql = 'INSERT INTO photosizes (photo_id, width, height, filename) VALUES ('
	."$imageid, $width, $height, '$file$ext')";
    $dbh->do($sql)
	|| warn "$sql\n".$dbh->errstr;
}

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
	&& $userinfo->{'editphotoentries'}
	&& defined($cgi->param('id')))
    {
	my @imagedirs = split(/,/, $cgi->param('id'));
	my ($dir, @status);
	foreach $dir (@imagedirs)
	{
	    push @status, "Processing $dir\n<br />";
	    if ($dir =~ /^\w+$/i)
	    {
		my (%alreadythere, %filedates);
		my ($sth, $row, $sql);

		if (open (I, "../images/$_/filedates.txt"))
		{
		    my (%months) =
			(
			 'Jan', '01',
			 'Feb', '02',
			 'Mar', '03',
			 'Apr', '04',
			 'Spring', '04',
			 'May', '05',
			 'Jun', '06',
			 'Jul', '07',
			 'Aug', '08',
			 'Sep', '09',
			 'Oct', '10',
			 'Nov', '11',
			 'Dec', '12',
			 'January', '01',
			 'February', '02',
			 'March', '03',
			 'April', '04',
			 'June', '06',
			 'July', '07',
			 'August', '08',
			 'September', '09',
			 'October', '10',
			 'November', '11',
			 'December', '12',
			 );

		    while (<I>)
		    {
			if (/^([a-z\-]+) +(\d+) +([a-z0-9]+) +([a-z0-9]+) +(\d+) ([A-Z][a-z][a-z]) ([ 0-9]\d) ([ 0-9]\d\:\d\d| \d\d\d\d) (.*).(jpg|thm)$/i)
			{
			    my ($name, $mo,$d,$y,$h,$m);
			    $y = $8;
			    $mo = $months{$6};
			    $d = $7;
			    $h = 0;
			    $m = 0;
			    $name = $9;
			    if ($y =~ /^([ 0-9]+)\:([0-9]+)$/)
			    {
				$h = $1;
				$m = $2;
				$y = (localtime(time))[5];
				$y-- if ($mo > (localtime(time))[4] + 1);
			    }
			    $filedates{$name} =
				printf("%04.4d-%02.2d-%02.2d %02.2d:%02.2d:00",
					$y,$mo,$d,$h,$m);
			    
			}
		    }
		    close I;
		}


		$sql = "SELECT id, name FROM photos WHERE directory='$dir'";

		$sth = $dbh->prepare($sql)
		    || die "$sql\n".$dbh->errstr;
		$sth->execute
		    || die "$sql\n".$sth->errstr;
		while ($row = $sth->fetchrow_arrayref)
		{
		    $alreadythere{$row->[1]} = $row->[0];
		}

		my ($currfile, %rootprocessed);
		push @status, "About to run /usr/local/bin/jhead\n<br />";
		foreach my $extension ( 'jpg', 'thm', 'JPG' )
		{
		    if (open(JPEGINFO, "/usr/local/bin/jhead /home/flutterby/public_html/images/$dir/*.$extension|"))
		    {
			push @status, "Opened JPEGINFO!\n<br />";
			while (<JPEGINFO>)
			{
			    push @status, "$_<br>";
			    if (/^(.*?) *: +(.*)$/)
			    {
				my ($att, $val);
				$att = $1;
				$val = $2;
				
				if ($att eq 'File name')
				{
				    if (defined($currfile))
				    {
					processcurrentfile($dbh, $userinfo, $dir,$currfile,\@status,\%rootprocessed,\%alreadythere);
				    }
				    $currfile = {};
				}
				$currfile->{$att} = $val;
			    }
			}
			processcurrentfile($dbh, $userinfo, $dir,$currfile,\@status,\%rootprocessed,\%alreadythere) if (defined($currfile));
			
			close JPEGINFO;
			$dbh->commit();
		    } # end of opening jpeginfo
		    else
		    {
			push @status, "unable to open JPEGINFO";
		    }
		}
	    } # end of if the directory was acceptable
	    my ($tree) =
	      Flutterby::HTML::LoadHTMLFileAsTree($configuration->{-htmlpath}.'importphoto.html');
	    my ($variables);
	    $variables = Flutterby::Users::GetWeblogInfo($cgi, $dbh);
	    $variables->{'userinfo_id'} = $dbh->quote($userinfo->{'id'});
	    $variables->{'status'} = join("\n",@status);

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
	} # end for each imagedir
    }
    else
    {
	Flutterby::Users::PrintLoginScreen($configuration,
					   $cgi, 
					   $dbh, 
					   './userinfo.cgi',
					   $loginerror);
    }
    $dbh->disconnect;
}
&main;


