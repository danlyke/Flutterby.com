#!/usr/bin/perl -w
use strict;
use CGI;
#use CGI::Carp qw(fatalsToBrowser);
use DBI;
use lib 'flutterby_cms';
use vars qw($configuration @editablefields);
use Flutterby::Config;
$configuration ||= Flutterby::Config::load();
use Flutterby::HTML;
use Flutterby::Output::HTMLProcessed;
use Flutterby::Parse::HTML;
use Flutterby::Parse::Text;
use Flutterby::Parse::String;
use Flutterby::Users;
use Flutterby::DBUtil;


@editablefields =
    (
     'email',
     'password',
     'lid_url',
     'homepage_url',
     'weblog_url',
     'weblog_name',
     'adbanner_url',
     'bio_text',
     'bio_texttype',
     'textentryrows',
     'textentrycols',
     'emailverified',
     'showemailinnntpversion',
    );

sub main
{
    my ($cgi, $dbh,$userinfo,$loginerror);
    $dbh = DBI->connect($configuration->{-database},
                        $configuration->{-databaseuser},
                        $configuration->{-databasepass})
        or die "DBH: $dbh\nDatabase: $configuration->{-database}\n"
            ."User: $configuration->{-databaseuser}\n"
                ."Password: $configuration->{-databasepass}\n"
                    ."DBI Error: ".$DBI::errstr."\ndollarbang: $!\n";
	$dbh->{AutoCommit} = 1;
    $cgi = new CGI;

    ($userinfo,$loginerror) = Flutterby::Users::CheckLogin($cgi,$dbh);

    if (defined($userinfo->{'id'})) {
        my ($terms);

        $terms = ' id='.$dbh->quote($userinfo->{'id'});
        $cgi->param('_id' => $userinfo->{'id'});
        $cgi->param('_password' => $cgi->param('_password1'))
            if ($cgi->param('_password1') && 
                $cgi->param('_password1') eq $cgi->param('_password2'));
        $cgi->param('_password1' => '');
        $cgi->param('_password2' => '');

        if (defined($cgi->param('_email'))) {
            if ($cgi->param('_email') eq $userinfo->{'email'}
                && $userinfo->{'emailverified'}) {
                $cgi->param('_emailverified' => 'true');
            } else {
                $cgi->param('_emailverified' => 'false');
            }
        }

        if (defined($cgi->param('_email'))) {
            $cgi->param('_showemailinnntpversion' =>
                        (defined($cgi->param('_showemailinnntpversion'))
                         ? 'true':
                         ($userinfo->{'showemailnntpversion'} 
                          ? 'true' : 'false')));
        }

	
        $cgi->param('textentryrows' => $userinfo->{'textentryrows'})
            unless (defined($cgi->param('textentryrows')) && 
                    $cgi->param('textentryrows') =~ /^\d+$/);
        $cgi->param('textentrycols' => $userinfo->{'textentrycols'})
            unless (defined($cgi->param('textentrycols'))
                    && $cgi->param('textentrycols') =~ /^\d+$/);

        Flutterby::Users::UpdateUser($cgi,$dbh,
                              \@editablefields,
                              $terms);

        $cgi->param('_password1' => '');
        $cgi->param('_password2' => '');
        my ($variables);
        $variables = Flutterby::Users::GetWeblogInfo($cgi, $dbh);


        if (defined($cgi->param('_showcommentsreversed'))) {
            my ($sql);
    
            $sql = 'UPDATE capabilities SET showcommentsreversed='
                .$dbh->quote($cgi->param('_showcommentsreversed'))
                    ." WHERE user_id=$userinfo->{'id'} AND weblog_id=$variables->{'fcmsweblog_id'}";
            $dbh->do($sql)
                || print STDERR "$sql\n".$dbh->errstr."\n";
        }


        my ($tree) = 
            Flutterby::HTML::LoadHTMLFileAsTree($configuration->{-htmlpath}.'userinfo.html');

        $variables->{'userinfo_id'} = $dbh->quote($userinfo->{'id'});
    
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
            );
        $out->output($tree);
    } else {
        Flutterby::Users::PrintLoginScreen($configuration,
                                           $cgi, $dbh,
                                           './userinfo.cgi',
                                           $loginerror);
    }
    $dbh->disconnect;
}
&main;
