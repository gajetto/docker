#!/usr/bin/perl -w
use lib '/acep_handler';
use DBI;
use Mail::Send;
use Data::Dumper;
use Config::INI::Simple;
use XML::Parser;
use XML::Simple;
use HTML::Table;
use Proc::ProcessTable;
use ExtSender;
use Getopt::Long;
use Attribute::Handlers;
use Encode;
use POSIX; 
no warnings 'redefine';
use constant ADMIN_MAIL=>'Alexey.Hohlov@acronis.com';
use constant REPORT_MAIL=>'cep@cepservice.ru.corp.acronis.com';
use constant TOP_LEVEL_LOG=>'/var/log/acep.log';
use constant CONFIGPATH=>'/etc/crash.conf';
use constant ATTACH_NAME=>'Report.xml';
exit;#Uncomment
our $queries={
	select_id=>'SELECT id FROM data WHERE currenthandle=0 LIMIT 1',
	stick_query_to_handle=>'UPDATE data SET currenthandle=1, datehandle=NOW() WHERE currenthandle=0 AND id=?',
	select_data=>'SELECT rawdata,hostname,addr,date FROM data WHERE currenthandle=1 AND id=?',
	stick_data_as_wrong=>'UPDATE data SET currenthandle=2, datehandle=NOW() WHERE currenthandle=1 AND id=? ',
	delete_handled_report=>'DELETE FROM data WHERE id=?'
};

our $LOGLEVEL={'info'=>0,'critical'=>1};
our $access_fields={"problem_report_version"=>1, "problem_report_product"=>1, "problem_report_ip"=>1,"problem_report_xml"=>1,"problem_report_datetime"=>1};
our $types=		{0       =>      "ReportTypeUndefined",
                                1       =>      "AutomaticVmGeneratedReport",
                                2       =>      "AutomaticDispatcherGeneratedReport",
                                3       =>      "UserDefinedOnStopedVmReport",
                                4       =>      "UserDefinedOnRunningVmReport",
                                5       =>      "UserDefinedOnConnectedServer",
                                6       =>      "UserDefinedOnDisconnectedServer",
                                7       =>      "UserDefinedOnNotRespondingVmReport",
                                8       =>      "AutomaticDetectedReport",
                                9       =>      "AutomaticStatisticsReport",
                                10      =>      "AutomaticInstalledSoftwareReport",
                                11      =>      "AutomaticVzStatisticReport"};
our ($dbh,$sth,$rawdata,$hostname,$addr,$date,$stop_process,$maxnumberprocesses,$hostnamedb,$dbname,$port,$username,$password,$next_iteration);
GetOptions ("forkprocesses=i" => \$maxnumberprocesses); 
die "Script should be run with param --forkprocesses=MAX_NUMBER_HANDLERS" unless $maxnumberprocesses;
setdbconnectparams();
open STDOUT,'>/dev/null';
open STDERR, '>/dev/null';
$SIG{HUP} = \&stop_process;
fork_process();


sub fork_process{
	exit if get_number_processes()>$maxnumberprocesses;
	if (my $pid=fork())
	{
		fork_process();
	}
	else
	{
		prepare_mysql_indexes();
		while(!$stop_process) {
			$next_iteration=0;
			handle()
		} ;
	}
}

sub UNIVERSAL::Override :ATTR
{
        my $ref=$_[2];
        *{$_[1]}=sub{&$ref unless $next_iteration};
}


sub prepare_mysql_indexes{
	$dbh=get_dbh();
	map{$sth->{$_}=$dbh->prepare($queries->{$_})}keys %$queries;
}

sub stop_process{
	$stop_process=1;
}

sub get_number_processes{
        my  $t = new Proc::ProcessTable;
	my $processes=scalar grep{$_->cmndline=~m/$0/} @{$t->table};
	return $processes;
}

sub handle{
	$sth->{'select_id'}->execute();
	my $id_ref=$sth->{'select_id'}->fetchrow_hashref();
	if ($id_ref->{id})
	{
		my $status=$sth->{'stick_query_to_handle'}->execute($id_ref->{id});
		handle_query($id_ref->{id}) unless ($status==0);#don't change to -" if $status;", because this will be not work!!!
	}
	
}


sub handle_query: Override{
	my $id=shift;
	smartlogger("Begin handle query with id=$id ,handler process id $$",1,1);
	$sth->{'select_data'}->execute($id);
	my $data=$sth->{'select_data'}->fetchrow_hashref();
	($rawdata,$hostname,$addr,$date)=map{$data->{$_}}qw(rawdata hostname addr date);
	parse_raw_data($id);
	
}

sub parse_raw_data: Override{
	my $id=shift;
	my $dropchar;
	$rawdata=~s/\x{1}\x{2}\x{3}\x{4}\x{5}\x{6}\x{7}\x{8}\cK/ /gs;;
	$rawdata = encode("UTF-8", decode("UTF-8", $rawdata));#Symbols which don't exists to UTF8 will be skipped
	my ($data_slice,$length_content)=({},length($rawdata));
	while ($rawdata =~ /([a-z_]+)\((\d+),([a-z_]+)\)=/g) {
		if ($2<$length_content){
			if ($access_fields->{$1})
			{
				$data_slice->{$1}={type=>$3,data=>substr($rawdata,pos $rawdata,$2)};
			}
			else
			{
				data_wrong($id,"Field $1 is't  access field");
			}
		}
		else{
			data_wrong($id,"Size content of parameter more size of data or name parameter is't mandatory");
		}
  	}
	data_wrong($id,"Parameter 'problem_report_xml' not found") unless $data_slice->{'problem_report_xml'};
	return 0 if $next_iteration;
	my $problem_report_xml=$data_slice->{'problem_report_xml'}->{'data'};
	my $table=build_table($problem_report_xml,$id,$data_slice);
	return 0 if $next_iteration;
	my $description=$data_slice->{'problem_report_product'}->{'data'}.' '.$data_slice->{'problem_report_version'}->{'data'};
	if(ExtSender::send(REPORT_MAIL,$table,$problem_report_xml,ATTACH_NAME,$description)){
		$sth->{'delete_handled_report'}->execute($id);
		smartlogger("Report with id $id was success delivered",1,1);
	}
	else{
		data_wrong($id,"Unsuccess delivery report");
	}

}


sub build_table: Override{
	my ($problem_report_xml,$id,$data_slice)=@_;
	my $parse = new XML::Parser(Style => 'Debug');
        eval '$parse->parse($problem_report_xml);';
        data_wrong($id,"XML is wrong $@") if ($@);	
	return 0 if $next_iteration;
	my $parsed_data;
	my $table = new HTML::Table(-border=>1);
	my $xs = XML::Simple->new();
        my $xml_parsed = $xs->XMLin($problem_report_xml);
	$table->addRow('<p align="center"><b>Field</b></p>','<p align="center"><b>Value</b></p>');
	$table->setCellBGColor(1, 1,'#CCCCFF' );
	$table->setCellBGColor(1, 2,'#CCCCFF' );
	$table->addRow('ReportId', "#$id");	
	$table->addRow('Product',$data_slice->{'problem_report_product'}->{'data'});
	$table->addRow('Version', $data_slice->{'problem_report_version'}->{'data'});
	$table->addRow('HostIp',$addr);
       	$table->addRow('DateTime', $date);
	$table->addRow('ReportType', $types->{$xml_parsed->{'Type'}}) if $xml_parsed->{'Type'};
	
	if ($xml_parsed->{'License'})	
	{
		map{$table->addRow('License.'.$_,$xml_parsed->{'License'}->{$_})}qw(User Company Key) ;	
	}
	if ($xml_parsed->{'HostInfo'})
        {
	                my $host_section_xml=$xml_parsed->{'HostInfo'};
                       	eval '$parse->parse($host_section_xml);';
                        if ($@){
										

                        }
                        else{
				my $host_info = $xs->XMLin($xml_parsed->{'HostInfo'});
				$table->addRow('HostInfo.Os', $host_info->{'OsVersion'}->{'StringPresentatio'});
				$table->addRow('HostInfo.CpuId', $host_info->{'Cpu'}->{'Model'});			
				$table->addRow('HostInfo.CpuNo', $host_info->{'Cpu'}->{'Number'});	
				$table->addRow('HostInfo.MemSize', $host_info->{'MemorySettings'}->{'HostRamSize'});			
				$table->addRow('HostInfo.MemLimit', $host_info->{'MemorySettings'}->{'ReservedMemoryLimit'});
			}
	}	
	$table->addRow('Description',$xml_parsed->{'ProblemTypeDescr'});
	return  $table->getTable;
}

sub data_wrong{
	my ($id,$message)=@_;
	$sth->{'stick_data_as_wrong'}->execute($id);
	logger("Report id:$id.  ".$message);
	$next_iteration=1;
}

sub get_dbh{	
        my $dbh=DBI->connect("DBI:mysql:$dbname:$hostnamedb:$port",$username,$password) or smartlogger("Can\'t connect to database $dbname:$hostnamedb:$port,$username,$password $@",1,0);
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
	die 'Section "DBDATA" not found inside config file '.CONFIGPATH	unless $config->{DBDATA};
        return $config->{DBDATA};

}

sub smartlogger{
        my ($message,$level,$not_send_mail)=@_;
        logger($message);
       	sendMail($message) unless $not_send_mail;
       	$next_iteration=($level == $LOGLEVEL{'critical'})?1:0;
	
}

sub sendMail{
        my $message=shift;
        require Mail::Send;
        my $msg = Mail::Send->new;
        my $to=ADMIN_MAIL;
        $msg = Mail::Send->new(Subject => 'CES service doesn\'t work', To=>$to);
        my $fh = $msg->open;
        print $fh $message;
        $fh->close;
}

sub logger{
        my $message=shift;
        require Log::Handler;
        my $log_file=TOP_LEVEL_LOG;
        if (-f $log_file)
        {
                my $log = Log::Handler->new();
                $log->add(file => {filename => $log_file, mode  => 'append', maxlevel => 'info',timeformat=> '%H:%M:%S',message_layout => '%D %T [%L] %m'});
                $log->info($message."\n");
        }

}


