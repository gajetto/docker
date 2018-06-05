#!/usr/bin/perl -w
use strict;
use lib qw(/acep_handler);
use DBI;
use Mail::Send;
use Config::INI::Simple;
use constant MAXNUMBER=>1000;
use constant CONFIGPATH=>'/etc/crash.conf';
use constant ADMIN_MAIL=>'ACEP-Maintaince-Group@acronis.com';
our ($rawdata,$hostname,$addr,$date,$stop_process,$maxnumberprocesses,$hostnamedb,$dbname,$port,$username,$password,$next_iteration);
my $dbh=get_dbh();
my $sth=$dbh->prepare('SELECT count(*) AS cnt FROM data');
$sth->execute();
my $row=$sth->fetchrow_hashref();
exit;

sendMail($row->{cnt})	if $row->{cnt}>=MAXNUMBER;

sub sendMail{
	my $rows=shift;
        my $msg = Mail::Send->new;
        my $to=ADMIN_MAIL;
        $msg = Mail::Send->new(Subject => 'Limit exceeded number of records', To=>$to);
        my $fh = $msg->open;
        print $fh 'Number of records in CES database more than '.MAXNUMBER."($rows)";
        $fh->close;
}


sub get_dbh{
	setdbconnectparams();
       	my $dbh=DBI->connect("DBI:mysql:$dbname:$hostnamedb:$port",$username,$password) or die("Can\'t connect to database $dbname:$hostnamedb:$port,$username,$password $@",1,0);
        return $dbh;
}


sub setdbconnectparams{
        my $config=get_config_db();
        ($hostnamedb,$dbname,$port,$username,$password)=map{$config->{$_}}qw(HOST NAME PORT USER PASSWORD);
}

sub get_config_db{
        my $config=Config::INI::Simple->new();
        die 'Config not found by path '.CONFIGPATH unless -f CONFIGPATH;
        $config->read(CONFIGPATH);
        die 'Section "DBDATA" not found inside config file '.CONFIGPATH unless $config->{DBDATA};
        return $config->{DBDATA};

}

