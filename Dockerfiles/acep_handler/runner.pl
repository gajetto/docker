#!/usr/bin/perl -w
use Proc::ProcessTable;
my $t = new Proc::ProcessTable;

my $flag=1;
my $flag_mysql=1;
foreach $p (@{$t->table}) {
  foreach $f ($t->fields){
        my $process=$p->{$f};
        if ($process &&($process=~m/acep_handler_post\.pl/))
        {
                $flag=0;
        }
	if ($process &&($process=~m/mysql/))
        {
		$flag_mysql=0;
        }

  }
}

if ($flag_mysql)
{
	system('systemctl start mariadb');
}

if ($flag)
{
        system('/acep_handler/acep_handler_post.pl --forkprocesses=1')
}
