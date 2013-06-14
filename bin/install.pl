#!/usr/bin/perl -w
use strict;
use lib '.';
use lib './flutterby_cms';
use File::Find;
use Data::Dumper;
use Term::ReadLine;


my ($term,$OUT);
$term = new Term::ReadLine 'Flutterby Content System installer';
$OUT = $term->OUT || \*STDOUT;


my ($foundparser);
$foundparser = 1 if eval {use Flutterby::HTML;1;};

my ($configfilename);
$configfilename = '.flutterby_cms';
$configfilename = "$ARGV[0]" if ($#ARGV >= 0);

my ($forcecopy, $verbosemessages);
my ($flutterbycmspath, # Path to the Flutterby modules and ./cgi ./html etc
    $fcmsinstallpath, $urlpath);
my (%modulesused);
my (@htmlfiles,@cgifiles,@binfiles);

$flutterbycmspath = '.' if (-d './Flutterby');
$flutterbycmspath = './flutterby_cms' if (-d './flutterby_cms/Flutterby');

die "Unable to find flutterbycms\n" unless defined $flutterbycmspath;

$fcmsinstallpath = '/home/danlyke/flutterby/installfcms';
$urlpath = '/archives/';
$forcecopy = 1;
$verbosemessages = 1;



sub
ReadConfig($@)
{
    my ($configoptions, @filesearchspec) = @_;
    my ($opened, $filename);

    while (!defined($opened) && $#filesearchspec >= 0)
    {
	$filename = shift @filesearchspec;

	$opened = open(CONFIGFILE, $filename);
    }

    if (!defined($opened))
    {
	print STDERR 'Unable to open any of '
	    .join(', ', @filesearchspec)."\n";
	return undef;
    }
    
    print "Reading $filename\n";
    while (<CONFIGFILE>)
    {
	if (/^\s*(\w+)\s*\:\s*(.*?)(\#.*)?$/)
	{
	    print "adding config option -$1 = $2\n";
	    $configoptions->{"\-$1"} = $2;
	}
    
    }
    close CONFIGFILE;
    return $configoptions;
}

my ($configoptions);
$configoptions = 
{
#    -database => 'DBI:Pg:dbname=flutterbycms',
#    -databaseuser => 'danlyke',
#    -databasepass => 'danlyke',
#    -htmlpath => "$fcmsinstallpath/htmltemplates/",
    -classcolortags => 		   
    {
	'body' => 
	{
	    'wb' => 
	    {
		'text' => '#AAFFFF',
		'bgcolor' => '#000000',
		'link' => '#aaaaff',
		'vlink' => '#aa66ff',
	    },
	    'pw' =>
	    {
		'text' => '#AAFFFF',
		'bgcolor' => '#000000',
		'link' => '#aaaaff',
		'vlink' => '#aa66ff',
	    },
	    'bw' =>
	    {
		'text' => '#000000',
		'bgcolor' => '#ffffff',
		'link' => '#0000ff',
		'vlink' => '#551a8b',
	    },
	    'pb' =>
	    {
		'text' => '#000000',
		'bgcolor' => '#ffffff',
		'link' => '#0000ff',
		'vlink' => '#551a8b',
	    },
	},
	'flutterbybodystandard' =>
	{
	    'wb' => 
	    {
		'text' => '#AAFFFF',
		'bgcolor' => '#000000',
		'link' => '#aaaaff',
		'vlink' => '#aa66ff',
	    },
	    'pw' => 
	    {
		'text' => '#AAFFFF',
		'bgcolor' => '#000000',
		'link' => '#aaaaff',
		'vlink' => '#aa66ff',
	    },
	    'bw' => 
	    {
		'text' => '#000000',
		'bgcolor' => '#ffffff',
		'link' => '#0000ff',
		'vlink' => '#551a8b',
	    },
	    'pb' =>
	    {
		'text' => '#000000',
		'bgcolor' => '#ffffff',
		'link' => '#0000ff',
		'vlink' => '#551a8b',
	    },
	},
    },
};


my ($thishostname);
$thishostname = `hostname`;
chomp($thishostname);
my (@requiredconfigoptions);

@requiredconfigoptions =
    (
     {
	 -name => 'database',
	 -default => 'DBI:Pg:dbname=flutterbycms',
	 -description => 'Database specification',
     },
     {
	 -name => 'databaseuser',
	 -default => 'dbusername',
	 -description => '',
     },
     {
	 -name => 'databasepass',
	 -default => 'dbpass',
	 -description => '',
     },
     {
	 -name => 'htmlpath',
	 -default => "$fcmsinstallpath/htmltemplates/",
	 -description => "Path into which to install the HTML template files",
     },
     {
	 -name => 'cgipath',
	 -default => "$ENV{'HOME'}/public_html/cgi-bin",
	 -description => "Path into which to install the cgi scripts",
     },
     {
	 -name => 'binpath',
	 -default => "$fcmsinstallpath/bin/",
	 -description => "Path into which to install the maintenance scripts, including tasks that\nwill run periodically",
     },
     {
	 -name => 'varpath',
	 -default => "$fcmsinstallpath/var/",
	 -description => "Path that various scripts can use for state management files, things which don't fit nicely into the database",
     },
     {
	 -name => 'packagepath',
	 -default => "$fcmsinstallpath/",
	 -description => "Path into which to install the Flutterby libraries",
     },
     {
	 -name => 'htmlroot',
	 -default => "$ENV{'HOME'}/public_html",
	 -description => 'path to the root of your HTML filesystem for static file generation',
     },
     );



unless (defined(ReadConfig($configoptions,
			   "./$configfilename",
			   "./flutterby_cms/$configfilename",
			   "$ENV{'HOME'}/$configfilename")))
{
    print $OUT "Creating a new config file in ./$configfilename\n";

    foreach (@requiredconfigoptions)
    {
	print $OUT "$_->{-description}\n" if (defined($_->{-description}));
	print $OUT "Example value: $_->{-default}\n" if (defined($_->{-default}));
	my ($val);
	$val = $term->readline("Value for $_->{-name}:");
	die "End of entry\n" unless defined($val);
	unless ($val =~ /\S/)
	{
	    $val = $_->{-default};
	    print "Using $val\n";
	}
	$configoptions->{"\-$_->{-name}"} = $val;
	$term->addhistory($val) if ($val =~ /\S/);
    }

    open O, ">./$configfilename"
	|| die "Unable to open ./flutterby_cms for writing\n";
    foreach (@requiredconfigoptions)
    {
	print O "# Value: $_->{-name}\n";
	print O "#   $_->{-description}\n";
	print O "$_->{-name}: ".$configoptions->{"\-$_->{-name}"}."\n\n";
    }
    
}


opendir D, "$flutterbycmspath/templates"
    || die "Unable to open $flutterbycmspath/templates\n";
@htmlfiles = grep { /\.html$/ } readdir D;
closedir D;

opendir D, "$flutterbycmspath/cgi"
    || die "Unable to open $flutterbycmspath/cgi\n";
@cgifiles = grep { /\.cgi$/ } readdir D;
closedir D;

opendir D, "$flutterbycmspath/bin"
    || die "Unable to open $flutterbycmspath/bin\n";
@binfiles = grep { -x "$flutterbycmspath/bin/$_" && -f "$flutterbycmspath/bin/$_" && !/^\./ && !/(\.bak|\~)$/ } readdir D;
closedir D;

print "$_\n" foreach (@cgifiles);


sub EnsureDirectory($)
{
    my ($dir);
    $dir = $_[0];

    print "Ensuring $dir\n"
	if (defined($verbosemessages));
    foreach $dir (@_)
    {
	my (@paths) = split /\/+/, $dir;
	my ($path, $p);
	shift @paths;
	pop @paths;
	
	while ($p = shift @paths)
	{
	    $path .= "/$p";
	    mkdir $path unless -d $path;
	}
    }
}


sub ProcessCGIFile($$)
{
    my ($sourcefile, $destfile) = @_;
    print "Processing CGI from $sourcefile to $destfile\n"
	if (defined($verbosemessages));

    if (open I, "$sourcefile")
    {
	my ($text, $line);
	while ($line = <I>)
	{
	    $line = "# $line" 
		if ($line =~ /^\s*use Flutterby::Config(new)?\s*.*?\;/);
	    $line = "use lib '$configoptions->{-packagepath}';\n"
		if ($line =~ /^\s*use\s+lib\s+[\'\"](.*?)[\'\"]\s*\;/);
	    if ($line =~ /^\s*(\$\w+)\s+(\|\|)?\=\s+Flutterby\:\:Config(new)?\:\:load\(.*?\)\;/)
	    {
		my ($var);
		$var = $1;
		$line = Dumper($configoptions);
		$line =~ s/\$VAR1/$var/;
	    }
	    $modulesused{$1} = 1
		if ($line =~ /^\s*use\s+(Flutterby::.*?)(\s.*?)?;/);
	    
	    $text .= $line;
	}
	close I;
	my ($outtext);
	$outtext = '';
	while ($text =~ s/^(.*?\=\s*)(Flutterby::HTML\:\:LoadHTMLFileAsTree\(.*?\)\s*\;)//xsi)
	{
	    my ($pre, $filetree) = ($1,$2);
	    if ($filetree =~ /\'(.*?)\'/ && -f "$flutterbycmspath/html/$1")
	    {
		$filetree = 
		    Dumper(Flutterby::HTML::LoadHTMLFileAsTree("$flutterbycmspath/html/$1"));
		$filetree =~ s/\$VAR1\s*\=//;
	    }
	    $outtext .= $pre.$filetree;
	}
	$text = $outtext.$text;
	$outtext = undef;

	open(O, ">$destfile.html")
	    || die "Unable to open $destfile for writing\n";
	print O $text;
	close O;
	unlink $destfile;
	rename "$destfile.html", $destfile;
	chmod 0755, $destfile;
    }
    else
    {
	warn "Unable to open $sourcefile\n";
    }
}



sub ProcessBinFile($$)
{
    my ($sourcefile, $destfile) = @_;
    print "Processing bin from $sourcefile to $destfile\n"
	if (defined($verbosemessages));

    if (open I, "$sourcefile")
    {
	my ($text, $line);
	while ($line = <I>)
	{
	    $line = "# $line" 
		if ($line =~ /^\s*use Flutterby::Config(new)?\s*.*?\;/);
	    $line = "use lib '$configoptions->{-packagepath}';\n"
		if ($line =~ /^\s*use\s+lib\s+[\'\"](.*?)[\'\"]\s*\;/);
	    if ($line =~ /^\s*(\$\w+)\s+(\|\|)?\=\s+Flutterby\:\:Config(new)?\:\:load\(.*?\)\;/)
	    {
		my ($var);
		$var = $1;
		$line = Dumper($configoptions);
		$line =~ s/\$VAR1/$var/;
	    }
	    $modulesused{$1} = 1
		if ($line =~ /^\s*use\s+(Flutterby::.*?)(\s.*?)?;/);
	    
	    $text .= $line;
	}
	close I;
	my ($outtext);
	$outtext = '';
#	while ($text =~ s/^(.*?\=\s*)(Flutterby::HTML\:\:LoadHTMLFileAsTree\(.*?\)\s*\;)//xsi)
#	{
#	    my ($pre, $filetree) = ($1,$2);
#	    if ($filetree =~ /\'(.*?)\'/ && -f "$flutterbycmspath/html/$1")
#	    {
#		$filetree = 
#		    Dumper(Flutterby::HTML::LoadHTMLFileAsTree("$flutterbycmspath/html/$1"));
#		$filetree =~ s/\$VAR1\s*\=//;
#	    }
#	    $outtext .= $pre.$filetree;
#	}
	$text = $outtext.$text;
	$outtext = undef;

	open(O, ">$destfile")
	    || die "Unable to open $destfile for writing\n";
	print O $text;
	close O;
	chmod 0755, $destfile;
    }
    else
    {
	warn "Unable to open $sourcefile\n";
    }
}



sub ProcessHTMLFile($$)
{
    my ($sourcefile, $destfile) = @_;
    print "Processing HTML from $sourcefile to $destfile\n"
	if (defined($verbosemessages));

    if (open I, "$sourcefile")
    {
	my ($text, $line);
	while ($line = <I>)
	{
	    $text .= $line;
	}
	close I;
	open(O, ">$destfile")
	    || die "Unable to open $destfile\n";
	print O $text;
	close O;
    }
    else
    {
	warn "Unable to open $sourcefile\n";
    }
}

sub FindHelperDeleteFiles()
{
    print "unlink $File::Find::name\n" if -e $File::Find::name;
}
sub FindHelperInstallPerlModules()
{
    my ($module, $filename);
    $module = $File::Find::name;
    $filename = $File::Find::name;
    if ($module =~ s/\.pm$// && -f $_)
    {
	$filename =~ s/$flutterbycmspath\//$configoptions->{-packagepath}\//;
#	$module =~ s/$flutterbycmspath\///;
#	$module =~ s/\//::/g;
#	print "Copy or link $File::Find::name into $configoptions->{-packagepath}\n"
#	    if ($modulesused{$module});
	my ($text);
	open(I, $File::Find::name)
	    || die "Unable to open $File::Find::name for reading\n";
	$text = join '', <I>;
	close I;
	EnsureDirectory($filename);
	open(O, ">$filename")
	    || die "Unable to open $filename for writing\n";
	print O "$text";
	close O;
    }
}

#$configoptions->{-htmlpath} = "$fcmsinstallpath/htmltemplates/";

EnsureDirectory("$configoptions->{-cgipath}/.");
EnsureDirectory("$configoptions->{-htmlpath}/.");
EnsureDirectory("$configoptions->{-binpath}/.");

my ($file);
print "Checking CGIFiles: ".join(', ', @cgifiles)."\n";
foreach $file (@cgifiles)
{
    print "Examing CGI $file for rebuild\n"
	if (defined($verbosemessages));
    if (defined($forcecopy)
	|| !-f "$configoptions->{-cgipath}/$file"
	|| -A "$flutterbycmspath/cgi/$file" > -A "$configoptions->{-cgipath}/$file")
    {
	ProcessCGIFile("$flutterbycmspath/cgi/$file",
		       "$configoptions->{-cgipath}/$file");
    }
}


foreach $file (@htmlfiles)
{
    print "Examing $file for rebuild\n"
	if (defined($verbosemessages));
    if (defined($forcecopy)
	|| !-f "$configoptions->{-htmlpath}/$file"
	|| -A "$configoptions->{-htmlpath}/$file" 
	> -A "$flutterbycmspath/html/$file")
    {
	ProcessHTMLFile("$flutterbycmspath/html/$file",
		       "$configoptions->{-htmlpath}/$file");
    }
}

my ($file);
foreach $file (@binfiles)
{
    print "Examing bin $file for rebuild\n"
	if (defined($verbosemessages));
    if (defined($forcecopy)
	|| !-f "$configoptions->{-binpath}/$file"
	|| -A "$flutterbycmspath/bin/$file" > -A "$configoptions->{-cgipath}/$file")
    {
	ProcessBinFile("$flutterbycmspath/bin/$file",
		       "$configoptions->{-binpath}/$file");
    }
}


#if (-d $fcmsinstallpath)
#{
#    find({ wanted => \&FindHelperDeleteFiles, no_chdir => 1},
#	 $fcmsinstallpath);
#}

foreach (keys %modulesused)
{
    print "used module $_\n";
}

print "Finding $flutterbycmspath/Flutterby\n";
find ({wanted => \&FindHelperInstallPerlModules, no_chdir => 1 },
      "$flutterbycmspath/Flutterby");


