package ExtSender;
use MIME::QuotedPrint;
use MIME::Base64;
use Mail::Sendmail 0.75; # doesn't work with v. 0.74!

sub send{
	my ($to,$text,$data,$attachname,$description)=@_;
%mail = (
         from =>$to,
         to => $to,
         subject => $description,
        );


$boundary = "====" . time() . "====";
$mail{'content-type'} = "multipart/mixed; boundary=\"$boundary\"";

$message = encode_qp( $text);
$mail{body} = encode_base64($data);
$boundary = '--'.$boundary;
$mail{body} = <<END_OF_BODY;
$boundary
Content-Type: text/html; charset="utf-8"
Content-Transfer-Encoding: quoted-printable

$message
$boundary
Content-Type: application/octet-stream; name="$attachname"
Content-Transfer-Encoding: base64
Content-Disposition: attachment; filename="$attachname"

$mail{body}
$boundary--
END_OF_BODY

return sendmail(%mail)?1:0;

}

1;
