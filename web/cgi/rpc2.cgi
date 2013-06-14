#!/usr/bin/perl -w
use strict;
use CGI;
use Apache;
use Frontier::RPC2;
use DBI;



use DBI;
my ($dbh);
$dbh = DBI->connect('DBI:Pg:dbname=flutterbycms',
		    'danlyke',
		    'danlyke')
    or die $DBI::errstr;
$dbh->{AutoCommit} = 1;


if (defined($ENV{'REQUEST_METHOD'}) && $ENV{'REQUEST_METHOD'} eq 'POST')
{
    my ($in);
    if (read(STDIN, $in, $ENV{'CONTENT_LENGTH'}))
    {
	my ($call, $args, $result, $coder);

	$coder = new Frontier::RPC2;
	$call = $coder->decode($in);
	$args = $call->{'value'};

	print STDERR "Got call $call->{'method_name'}\n";
	if ($call->{'method_name'} eq 'blogger.newPost')
	{
	    my ($appkey, $blogid, $username, $password,$content, $publish)
		= @$args;

	    $blogid =~ s/^entry//;
	    print STDERR "app key $appkey, blog id $blogid\n";

	    my ($sql, $h);
	    $sql = 'SELECT id AS userid, name AS nickname, email AS email, '
		.'name AS lastname, name AS firstname, homepage_url AS url '
		    .'FROM USERS WHERE name='
			.$dbh->quote($username).' AND password='
			    .$dbh->quote($password);
	    if ($h = $dbh->selectrow_hashref($sql))
	    {
		my ($id) = $dbh->selectrow_array("SELECT nextval('articles_id_seq')");
		$sql = 'INSERT INTO articles (id, author_id, trackrevisions, text,texttype) VALUES ('
		    .join(',',
			  $id, $h->{'userid'}, 'true',
			  $dbh->quote($content),
			  $dbh->quote(1)).')';
		print STDERR "$sql\n";
		if ($dbh->do($sql))
		{
		    $sql = 'INSERT INTO weblogcomments(entry_id, article_id) '
			.'VALUES ('.$dbh->quote($blogid).", $id )";
		
		    if ($dbh->do($sql))
		    {
			$dbh->commit();
			$result = $coder->encode_result($id);
		    }
		    else
		    {
			$result = $coder->encode_fault(4, "Unable to insert into comments table: "
						      .$dbh->errstr);
			print STDERR  "Unable to insert into comments table: "
			    .$dbh->errstr."\n";
		    }
		}
		else
		{
		    $result = $coder->encode_fault(4, "Unable to insert article: "
						  .$dbh->errstr);
		    print STDERR  "Unable to insert article: "
			.$dbh->errstr."\n";
		}
	    }
	    else
	    {
		$result = $coder->encode_fault(4, "Apparently invalid user");
		print STDERR  "Apparently invalid user\n";
	    }
	}
	elsif ($call->{'method_name'} eq 'blogger.editPost')
	{
	    my ($appkey, $postid, $username, $password,$content, $publish)
		= @$args;

	    my ($sql, $h);
	    $sql = 'SELECT id AS userid, name AS nickname, email AS email, '
		.'name AS lastname, name AS firstname, homepage_url AS url '
		    .'FROM USERS WHERE name='
			.$dbh->quote($username).' AND password='
			    .$dbh->quote($password);
	    if ($h = $dbh->selectrow_hashref($sql))
	    {
		$sql = 'UPDATE articles SET text='
		    .$dbh->quote($content)
			." WHERE author_id=$h->{'userid'} AND id="
			    .$dbh->quote($postid);
		if ($dbh->do($sql))
		{
		    $dbh->commit();
		    $result = $coder->encode_result(1);
		}
		else
		{
		    $result = $coder->encode_fault(4, "Unable to update article"
						  .$dbh->errstr);
		    print STDERR  "Unable to update article"
			.$dbh->errstr."\n";
		}
	    }
	    else
	    {
		$result = $coder->encode_fault(4, "Apparently invalid user");
		print STDERR  "Apparently invalid user\n";
	    }
	    
	}
	elsif ($call->{'method_name'} eq 'blogger.getUsersBlogs')
	{
	    my ($appkey, $username, $password) = @$args;
	    my ($sql, $h);
	    $sql = 'SELECT id AS userid, name AS nickname, email AS email, '
		.'name AS lastname, name AS firstname, homepage_url AS url '
		    .'FROM USERS WHERE name='
			.$dbh->quote($username).' AND password='
			    .$dbh->quote($password);

	    print STDERR "looking for user $username\n";
	    if ($h = $dbh->selectrow_hashref($sql))
	    {
		print STDERR "Found user $h->{'userid'}\n";
		$sql = "SELECT 'entry'||weblogentries.id AS blogid,"
		    .'articles.title AS blogName,'
			."'http://www.flutterby.com/archives/viewentry.cgi?id='"
			    .'||weblogentries.id AS url '
				.'FROM articles, weblogentries WHERE '
				    .' articles.id = weblogentries.article_id '
					.'AND weblogentries.id=4541';
		my ($sth, $row);
		print STDERR "Preparing $sql\n";
		if ($sth = $dbh->prepare($sql))
		{
		    my (@a);
		    print STDERR "Executing $sql\n";
		    if ($sth->execute())
		    {
			while ($row = $sth->fetchrow_hashref)
			{
			    print STDERR "Pushing $row->{'blogid'}\n";
			    push @a, $row;
			}
			$result = $coder->encode_response(\@a);
		    }
		    else
		    {
			$result = $coder->encode_fault(4, "unable to execute ".$sth->errstr);
			print STDERR "unable to execute ".$sth->errstr."\n";
		    }
		}
		else
		{
		    $result = $coder->encode_fault(4, "Unable to get posts: "
						  .$dbh->errstr);
		    print STDERR  "Unable to get posts: "
			.$dbh->errstr."\n";
		}
		print STDERR "Processed\n";
	    }
	    else
	    {
		$result = $coder->encode_fault(4, 'blogger.getUserInfo failed');
		print STDERR  'blogger.getUserInfo failed'."\n";
	    }
	}
	elsif ($call->{'method_name'} eq 'blogger.getUserInfo')
	{
	    my ($appkey, $username, $password) = @$args;
	    my ($sql, $h);
	    $sql = 'SELECT id AS userid, name AS nickname, email AS email, '
		.'name AS lastname, name AS firstname, homepage_url AS url '
		    .'FROM USERS WHERE name='
			.$dbh->quote($username).' AND password='
			    .$dbh->quote($password);
	    if ($h = $dbh->selectrow_hashref($sql))
	    {
		$result = $coder->encode_response($h);
	    }
	    else
	    {
		$result = $coder->encode_fault(4, 'blogger.getUserInfo failed');
		print STDERR  'blogger.getUserInfo failed'."\n";
	    }
	}
	elseif (0 && $call->{'method_name'} eq 'blogger.getRecentPosts')
	{
	    my ($appkey, $blogid, $username, $password, $numberOfPosts) = @$args;
	    my ($sql, $h);
	    $sql = 'SELECT id AS userid, name AS nickname, email AS email, '
		.'name AS lastname, name AS firstname, homepage_url AS url '
		    .'FROM USERS WHERE name='
			.$dbh->quote($username).' AND password='
			    .$dbh->quote($password);
	    if ($h = $dbh->selectrow_hashref($sql))
	    {
		$result = $coder->encode_response($h);
	    }
	    else
	    {
		$result = $coder->encode_fault(4, 'blogger.getUserInfo failed');
		print STDERR  'blogger.getUserInfo failed'."\n";
	    }

#getRecentPosts(String appkey, String blogid, String username, String
#password, int numberOfPosts)	
	}
	else
	{
	    $result = $coder->encode_fault(7, 
					  "Unknown method $call->{'method_name'}");
	    print STDERR  
		"Unknown method $call->{'method_name'}\n";
	}

	my ($header);
	$header = "Content-Type: text/xml\nContent-Length: "
	    .length($result)."\n\n";


	my $r = Apache->request;
	$r->send_cgi_header($header);
	print STDERR "posting result $result\n";
	print $result;
	print STDERR "IN: ---\n$in\n----\n";
    }
}
else
{
    my ($cgi) = new CGI;
    print $cgi->header();

    print "<html><head><title>CGI variable test</title></head>\n";
    print "<body><h1>CGI variable test</h1>\n";
    foreach ($cgi->param())
    {
	print "<li><b>$_</b> ".$cgi->param($_)."</li>\n";
    }
    print "</ol><h2>Environment</h2><ol>";
    foreach (keys %ENV)
    {
	print "<li><b>$_</b> $ENV{$_}</li>\n";
    }
    print "</ol>";
    print "</body></html>\n";
}


$dbh->disconnect;

