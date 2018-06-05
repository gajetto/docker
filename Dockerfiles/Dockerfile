FROM centos:7

RUN (cd /lib/systemd/system/sysinit.target.wants/; for i in *; do [ $i == systemd-tmpfiles-setup.service ] || rm -f $i; done); \
rm -f /lib/systemd/system/multi-user.target.wants/*;\
rm -f /etc/systemd/system/*.wants/*;\
rm -f /lib/systemd/system/local-fs.target.wants/*; \
rm -f /lib/systemd/system/sockets.target.wants/*udev*; \
rm -f /lib/systemd/system/sockets.target.wants/*initctl*; \
rm -f /lib/systemd/system/basic.target.wants/*;\
rm -f /lib/systemd/system/anaconda.target.wants/*;

RUN yum update -y && yum install -y epel-release && yum install -y nginx mysql httpd && yum clean all && rm -rf /var/cache/yum
RUN mkdir /acep_handler /acep_handler_v20

COPY acep_handler /acep_handler
COPY acep_handler_v20 /acep_handler_v20
WORKDIR /acep_handler


EXPOSE 80
