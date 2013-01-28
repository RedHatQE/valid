#!/bin/bash
umask 0077
exec 1>/tmp/squid_setup.log
exec 2>&1

set -x
set -e

function rand_string() {
    # $1: length
    # $2: start (dec) into the ASCII table
    # $3: end (dec) into the ASCII table
    declare -i len=${1:-32}
    declare -i lo=${2:-40}
    declare -i hi=${3:-126}
    # sanity
    [ $len -gt 0 ] && [ $lo -gt 0 ] && [ $hi -gt 0 ] || return 1
    if [ $lo -gt $hi ] ; then
        local tmp=$hi
        hi=$lo
        lo=$tmp
    fi
    declare -i i=0
    declare -i val=0
    while [ $i -lt $len ] ; do
        i=$[ i + 1 ]
        val=$[ (RANDOM % (hi - lo)) + lo ]
        printf \\$[val/64*100+val%64/8*10+val%8]
    done
}


PROXY_PASSWORD=`rand_string`
PROXY_USER="rhui-client"

yum -y install squid httpd-tools
htpasswd -bc /etc/squid/passwd $PROXY_USER $PROXY_PASSWORD
echo 'auth_param basic program /usr/lib64/squid/basic_ncsa_auth /etc/squid/passwd' > /etc/squid/squid.conf.new
echo 'acl auth proxy_auth REQUIRED' >> /etc/squid/squid.conf.new
cat /etc/squid/squid.conf | sed 's,allow localnet,allow auth,' >> /etc/squid/squid.conf.new
mv -f /etc/squid/squid.conf.new /etc/squid/squid.conf
systemctl enable squid.service
systemctl start squid.service
iptables -I INPUT -p tcp --destination-port 3128 -j ACCEPT
service iptables save

cat <<__VARIABLES > /tmp/squid_setup_variables.sh
PROXY_PASSWORD=$PROXY_PASSWORD
PROXY_USER=$PROXY_USER
__VARIABLES
