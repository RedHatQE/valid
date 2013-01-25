#!/bin/bash
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

exit 0

sudo yum -y install squid httpd-tools
sudo htpasswd -bc /etc/squid/passwd $PROXY_USER $PROXY_PASSWORD
sudo echo 'auth_param basic program /usr/lib64/squid/ncsa_auth /etc/squid/passwd' > /etc/squid/squid.conf.new
sudo echo 'acl auth proxy_auth REQUIRED' >> /etc/squid/squid.conf.new
sudo cat /etc/squid/squid.conf | sed 's,allow localnet,allow auth,' >> /etc/squid/squid.conf.new
sudo mv -f /etc/squid/squid.conf.new /etc/squid/squid.conf
sudo service squid start
sudo chkconfig squid on
sudo iptables -I INPUT -p tcp --destination-port 3128 -j ACCEPT
sudo service iptables save
