#!/usr/bin/perl -w
use DBI;
use Data::Dumper;
my $dbh=DBI->connect('DBI:mysql:tmpcesdata','current','current') or die '';
$sth=$dbh->prepare('DELETE FROM data where id=22486256');
my $res=$sth->execute();
if ($res==1)
{
	print Dumper($res);
}
#ysql -u current --password='current' tmpcesdata
