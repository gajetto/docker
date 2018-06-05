#!/usr/bin/perl -w
use Proc::ProcessTable;
my $t = new Proc::ProcessTable;
foreach $p (@{$t->table}) {
  foreach $f ($t->fields){
        my $process=$p->{$f};
        if ($process &&($process=~m/acep_handler_post\.pl/))
        {
               	$p->kill(9);
        }
  }
}

