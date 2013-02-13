#! /usr/bin/python -tt

import argparse
import sys
import yaml
import re
import Queue
import threading
import boto
# import paramiko
import random
import logging
import string
import time
import urllib2
import base64

from boto import ec2

def randString(length=32):
    return ''.join(random.choice(string.ascii_lowercase) for x in range(length))


argparser = argparse.ArgumentParser(description='Create proxies, update data')
argparser.add_argument('--debug', action='store_const', const=True,
                      default=False, help='debug mode')
argparser.add_argument('--maxwait', type=int,
                       default=900, help='maximum wait time for instance creation')
argparser.add_argument('--numthreads', type=int,
                       default=8, help='number of worker threads')
argparser.add_argument(
    '--config',
    type=argparse.FileType('r'),
    default="/etc/validation.yaml",
    help='use supplied yaml config file'
)
argparser.add_argument('--force', action='store_const', const=True, default=False,
                       help="create proxy even if already present in data")
argparser.add_argument('--maxtries', type=int,
                       default=30, help='maximum number of tries')
argparser.add_argument('--settlewait', type=int,
                       default=30, help='wait for instance to settle before testing')
argparser.add_argument(
    '-p',
    '--password',
    default=randString(32),
    help='proxy password'
)
argparser.add_argument(
    '-u',
    '--user',
    default='rhui-client',
    help='proxy user'
)
argparser.add_argument(
    '--port',
    type=int,
    default=3128,
    help='proxy port'
)


argparser.add_argument(
    'data',
    type=argparse.FileType('rw'),
    help='data file to use'
)

operation = argparser.add_mutually_exclusive_group()
operation.add_argument('--terminate', action='store_true',
                      help="read data and terminate proxies found")
operation.add_argument('--check', action='store_true',
                      help="read data and try proxies found")
operation.add_argument('--create', action='store_true',
                      default=True, help="the default operation")

args = argparser.parse_args()
maxtries = args.maxtries
maxwait = args.maxwait
settlewait = args.settlewait

logging.getLogger('boto').setLevel(logging.CRITICAL)
if args.debug:
    loglevel = logging.DEBUG
    #logging.getLogger("paramiko").setLevel(logging.DEBUG)
else:
    loglevel = logging.INFO
    #logging.getLogger("paramiko").setLevel(logging.ERROR)

logging.basicConfig(
    level=loglevel,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%m/%d/%Y %I:%M:%S %p'
)

logging.debug("maxtries: %d" % args.maxtries)
logging.debug("maxwait: %d" % args.maxwait)
logging.debug("settlewait: %d" % args.settlewait)
logging.debug("numthreads: %d" % args.numthreads)
logging.info("user: %s" % args.user)
logging.info("password: %s" % args.password)


REGION_AMI = {
    "ap-northeast-1": "ami-5f01bb5e",
    "ap-southeast-1": "ami-30aeec62",
    "ap-southeast-2": "ami-9ae472a0",
    "eu-west-1": "ami-bafcf3ce",
    "sa-east-1": "ami-81558d9c",
    "us-east-1": "ami-6145cc08",
    "us-west-1": "ami-0899b94d",
    "us-west-2": "ami-0266ed32"
}

USER_DATA ='''\
#! /bin/bash
umask 0077
exec 1>/tmp/squid_setup.log
exec 2>&1
set -xe
yum -y install squid httpd-tools squid-sysvinit
htpasswd -bc /etc/squid/passwd '%(user)s' '%(password)s'
chown squid:squid /etc/squid/passwd
echo 'auth_param basic program /usr/lib64/squid/basic_ncsa_auth /etc/squid/passwd' > /etc/squid/squid.conf.new
echo 'acl auth proxy_auth REQUIRED' >> /etc/squid/squid.conf.new
cat /etc/squid/squid.conf | sed 's,allow localnet,allow auth,' >> /etc/squid/squid.conf.new
mv -f /etc/squid/squid.conf.new /etc/squid/squid.conf
systemctl enable squid.service
systemctl start squid.service
iptables -I INPUT -p tcp --destination-port %(port)d -j ACCEPT
service iptables save
''' % {'user': args.user, 'password': args.password, 'port': args.port}

logging.debug("proxy user data: \n%s" % USER_DATA)

mainq = Queue.Queue()
data_lock = threading.Lock()

try:
    data = None
    data = yaml.load(args.data)
except yaml.error.YAMLError as e:
    print >>sys.stderr, "unable to parse %s: %s" % (args.data.name, e)
except Exception as e:
    print >>sys.stderr, "got exception: %s" % e
finally:
    if not data:
        print >>sys.stderr, "got no data"
        sys.exit(1)
    args.data.close()

try:
    config = None
    config = yaml.load(args.config)
except yaml.error.YAMLError as e:
    print >>sys.stderr, "unable to parse %s: %s" % (args.config.name, e)
except Exception as e:
    print >>sys.stderr, "got exception: %s" % e
finally:
    args.config.close()
    if not config:
        print >>sys.stderr, "got no config data"
        sys.exit(1)

if 'ec2' not in config:
    print >>sys.stderr, "ec2 section not in %s" % args.config.name
    sys.exit(1)
if 'ec2-key' not in config['ec2']:
    print >>sys.stderr, "ec2-key not in %s['ec2']" % \
          args.config.name
    sys.exit(1)
if 'ec2-secret-key' not in config['ec2']:
    print >>sys.stderr, "ec2-secret-key not in %s['ec2']" % \
          args.config.name
    sys.exit(1)
ec2_key = config['ec2']['ec2-key']
ec2_secret_key = config['ec2']['ec2-secret-key']

class InstantiationError(Exception):
    pass

class InstanceThread(threading.Thread):
    def run(self):
        while True:
            logging.debug(self.getName() + ": task queue: %s" %yaml.dump(mainq.queue))
            if mainq.empty():
                # task queue empty; this being a single-shot app -> thread exits
                break
            try:
                (ntry, action, params) = mainq.get()
                mainq.task_done()
            except:
                continue
            if ntry > maxtries:
                logging.error(self.getName() + ": %s: %s failed after %d tries" %
                             (action, params, ntry))
                continue
            if action == 'instantiate':
                self.instantiate(ntry, params)
                continue
            if action == 'check':
                self.check(ntry, params)
                continue
            if action == 'terminate':
                self.terminate(ntry, params)
                continue
            raise Exception("INTERNAL: action %s unknown" % action)

    def instantiate(self, ntry, params):
        logging.debug(str((ntry, params)))
        region_name = params['region']
        if region_name not in REGION_AMI:
            raise InstantiationError(
                "INTERNAL: region %s not in %s" %
                (region_name, REGION_AMI)
            )
        try:
            task = None
            region = boto.ec2.get_region(
                region_name,
                aws_access_key_id=ec2_key,
                aws_secret_access_key=ec2_secret_key
            )
            region_connection = region.connect(
                aws_access_key_id=ec2_key,
                aws_secret_access_key=ec2_secret_key
            )

            # security group for squid
            security_group = region_connection.create_security_group(
                'squid-%s-%s' % (region_name, randString(8)),
                'a security group allowing port %s access' % args.port
            )

            security_group.authorize('tcp', args.port, args.port, '0.0.0.0/0')
            # ssh allowed for debugging purposes
            security_group.authorize('tcp', 22, 22, '0.0.0.0/0')
            # create proxy instance
            reservation = region_connection.run_instances(
                REGION_AMI[region_name],
                instance_type="t1.micro",
                key_name=params['key_name'],
                security_groups=[security_group],
                user_data=USER_DATA
            )
            instance = reservation.instances[0]
            count = 0
            while instance.update() == 'pending' and count < maxwait / 5:
                # waiting out instance to appear
                logging.info(self.getName() + ": proxy in %s pending; %d" %
                        (region_name, maxwait / 5 - count))
                count += 1
                time.sleep(5)
            region_connection.close()
            if instance.update() != 'running':
                raise InstantiationError(
                    "failed to instantiate proxy in %s" %
                     region_name
                )
            instance.add_tag("Name", "Squid")
            proxy = {
                'region': region_name,
                'host': instance.public_dns_name,
                'port': args.port,
                'user': args.user,
                'password': args.password,
                'id': instance.id,
                'group': {
                    'name': security_group.name,
                    'id': security_group.id
                }
            }
        except boto.exception.EC2ResponseError as e:
            logging.debug("got %s" % e)
            if "<Code>InstanceLimitExceeded</Code>" in str(e):
                logging.info("Instance limit reached in %s" % region_name)
                task = (ntry + 1, 'instantiate', params.copy())
            elif "<Code>InvalidParameterValue</Code>" in str(e):
                raise InstantiationError(
                    "Invalid parameter in: %s, %s, %s; skipping" %
                    (region_name, REGION_AMI[region_name], e)
                )
            elif "<Code>InvalidKeyPair.NotFound</Code>" in str(e):
                raise InstantiationError(
                    "Invalid key in config %s[ssh][%s]" %
                    (args.config.name, region_name)
                )
            else:
                logging.info("got %s" % e)
                task = (ntry * 1.66 + 1, 'instantiate', params.copy())
        else:
            # it worked!
            logging.info(self.getName() + ": created proxy: %s, %s" %
                        (region_name, instance.id))
            task = (0, 'check', proxy.copy())
        finally:
            if task is not None:
                logging.debug(self.getName() + ": scheduling: %s" % str(task))
                mainq.put(task)

    def check(self, ntry, proxy):
        proxy_handler = urllib2.ProxyHandler(
            {
                'https':
                    'https://%(user)s:%(password)s@%(host)s:%(port)s' % proxy
            }
        )
        proxy_auth_handler = urllib2.ProxyBasicAuthHandler()
        opener = urllib2.build_opener(proxy_handler, proxy_auth_handler,
                                     urllib2.HTTPHandler)
        urllib2.install_opener(opener)
        count = 0
        while count < maxwait / 5 :
            count += 1
            logging.info(self.getName() + ": trying google via proxy %s (%d)" %
                        (proxy['host'], maxwait / 5 - count))
            try:
                fd = opener.open('https://www.google.com/')
            except Exception as e:
                logging.debug(self.getName() + ": got %s" % e)
            else:
                logging.info(self.getName() + ": proxy %s: %s running" %
                           (proxy['region'], proxy['host']))
                fd.close()
                break
        if count >= maxwait / 5:
            logging.warning(self.getName() + ": proxy %s: %s not running" %
                          (proxy['region'], proxy['host']))
        with open(args.data.name, 'w+') as fd:
            # data is shared
            with data_lock:
                for entry in data:
                    if entry['region'] != proxy['region']:
                        continue
                    entry['proxy'] = proxy
                try:
                    yaml.dump(data, fd)
                except Exception as e:
                    logging.error(self.getName() + ":Couldn't update %s: %s" %
                                 (fd.name, e))
                else:
                    logging.info(self.getName() +": written %s" % fd.name)

    def terminate(self, ntry, proxy):
        try:
            task = None
            region = boto.ec2.get_region(
                proxy['region'],
                aws_access_key_id=ec2_key,
                aws_secret_access_key=ec2_secret_key
            )
            region_connection = region.connect(
                aws_access_key_id=ec2_key,
                aws_secret_access_key=ec2_secret_key
            )
            region_connection.terminate_instances(
                instance_ids=[proxy['id']]
            )
            instance = region_connection.get_all_instances(
                instance_ids=[proxy['id']]
            )[0].instances[0]
            count = 0
            while instance.update() != 'terminated' and count < maxwait / 5:
                # waiting out instance to appear
                logging.info(self.getName() + ": proxy  %s pending; %d" %
                        (proxy['id'], maxwait / 5 - count))
                count += 1
                time.sleep(5)
            if instance.update() != 'terminated':
                logging.warning("could not terminate instance: %s" %
                               proxy['id'])
                return
        except Exception as e:
            logging.warning("got %s deleting proxy: %s" %
                           (e, proxy))
            return

        if 'group' in proxy and \
        isinstance(proxy['group'], dict) and \
        'id' in proxy['group']:
             try:
                region_connection.delete_security_group(
                    group_id=proxy['group']['id']
                )
             except Exception as e:
                logging.warning("got %s deleting security group: %s" %
                               (e, proxy['group']))
                return

        # all OK, update the data dict
        with data_lock:
            with open(args.data.name, 'w+') as fd:
                # data is shared
                for entry in data:
                    if not isinstance(entry, dict):
                        logging.debug("skipped non-dict: %s" % entry)
                        continue
                    if 'proxy' in entry:
                            logging.debug("skipped non-proxy entry %s" % entry)
                            continue
                    if not isinstance(entry['proxy'], dict):
                            logging.debug("skipped non-dict-proxy: %s" % entry)
                            continue
                    if 'id' not in entry['proxy']:
                        logging.debug(
                            "skipped entry with a proxy lacking id: %s" %
                             entry
                        )
                        continue
                    if entry['proxy']['id'] != proxy['id']:
                        logging.debug(
                            "skipped entry with a non-matching proxy id: %s" %
                            entry
                        )
                        continue
                    # now just remove the proxy fields
                    del(entry['proxy'])
                # dump data
                try:
                    yaml.dump(data, fd)
                except Exception as e:
                    logging.error(self.getName() + ":Couldn't update %s: %s" %
                                 (fd.name, e))
                else:
                    logging.info(self.getName() +": written %s" % fd.name)





def create_proxies(data, ssh_config, force=False):
    regions = {}
    if not isinstance(data, list):
        print >>sys.stderr, "data not in list shape"
        sys.exit(1)
    for entry in data:
        logging.debug('processing %s' % yaml.dump(entry))
        if not isinstance(entry, dict):
            print >>sys.stderr, "data not in list of dicts shape: %s" % \
                  yaml.dump(entry)
            sys.exit(1)
        if 'region' not in entry:
            print >>sys.stderr, "region field missing in entry: %s" % \
                  yaml.dump(entry)
            sys.exit(1)
        if entry['region'] not in ssh_config:
            print >>sys.stderr, "region %s not configured in %s" % \
                  (entry['region'], args.config.name)
        if 'proxy' in entry and not force:
            logging.info("proxy field %(proxy)s present in %(region)s" % entry)
            continue
        if entry['region'] in regions:
            logging.debug('region %s already scheduled: %s' % \
                         (entry['region'],regions[entry['region']]))
            continue
        task = {
            'region': entry['region'],
            'key_name': ssh_config[entry['region']][0],
            'key_file': ssh_config[entry['region']][1],
        }
        regions[entry['region']] = task
        logging.info('scheduling task: %s' % str(task))
        mainq.put((0, 'instantiate', task))

def manipulate_proxies(data, action):
    proxies = {}
    if not isinstance(data, list):
        print >>sys.stderr, "data not in list shape"
        sys.exit(1)
    for entry in data:
        logging.debug('processing %s' % yaml.dump(entry))
        if not isinstance(entry, dict):
            logging.error("entry %s not dict; skipped" % entry)
            continue
        if 'proxy' not in entry:
            logging.debug("proxy field not present for %(ami)s" % entry)
            continue
        if not isinstance(entry['proxy'], dict):
            logging.debug("proxy field not dict: %: %s; skipped" %
                        (entry, args.config.name))
            continue
        if 'id' not in entry['proxy']:
            logging.debug("id field not present: %: %s; skipped" %
                         (entry['proxy'], args.config.name))
            continue
        if entry['proxy']['id'] in proxies:
            logging.debug('proxy %s already scheduled' %
                         entry['proxy']['id'])
            continue
        logging.info("processing %(region)s: %(host)s" % entry['proxy'])
        proxies[entry['proxy']['id']] = entry['proxy']
        mainq.put((0, action, entry['proxy'].copy()))

if args.check:
    logging.info("trying proxies in %s" % args.data.name)
    manipulate_proxies(data, "check")
    print "check"
if args.terminate:
    logging.info("terminating proxies in %s" % args.data.name)
    manipulate_proxies(data, "terminate")
if args.create:
    logging.info("terminating proxies for %s" % args.data.name)
    create_proxies(data, config['ssh'], args.force)


logging.debug("launching with a task queue: %s" %yaml.dump(mainq.queue))


for i in range(args.numthreads):
    i = InstanceThread()
    i.start()

try:
    threads_exist = True
    while threads_exist:
        threads_exist = False
        for thread in threading.enumerate():
            if thread is not threading.currentThread():
                threads_exist = True
                thread.join(2)
except KeyboardInterrupt:
    print "Got CTRL+C, exitting"
    for thread in threading.enumerate():
        if thread is not threading.currentThread() and thread.isAlive():
            try:
                thread._Thread__stop()
            except:
                print(str(thread.getName()) + 'could not be terminated')
    sys.exit(2)


