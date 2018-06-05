package HTTPS;
#use CGI::Util qw(escape);
#use Data::Dumper;
use LWP::UserAgent;
use HTTP::Request;
use Time::HiRes qw/time/;
#use constant ADDR=>'https://91.195.22.10:44443';
use constant ADDR=>'http://127.0.0.1:8091/acep-rest/save_xml';

sub send{
	my $parameters=shift;
	my @params_post='';
	my $ua = LWP::UserAgent->new;
	my $req = HTTP::Request->new(POST => ADDR);
	foreach my $key (keys %$parameters)
	{
		push(@params_post,"$key=$parameters->{$key}");
	}
	if (@params_post)
	{
		my $post_content=join('&',@params_post);
	       	$req->content_type('application/x-www-form-urlencoded');
	       	$req->content($post_content);

		
		
	       	my $res=$ua->request($req);
		if ($res->status_line=~m/Can\'t\s+connect/)
                {
                                return 0;
                }
		else
		{
			return $res->content;
		}
	}
	return 0;

}

1;
