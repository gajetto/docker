#!/bin/sh
/usr/local/nginx/sbin/nginx -s stop
sleep 2s
service httpd stop
sleep 2s
service httpd start
sleep 2s
/usr/local/nginx/sbin/nginx
