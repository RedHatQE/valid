#! /usr/bin/python -tt

import argparse
import sys
import yaml
import re
import Queue
import threading
import boto
import paramiko
import random
import logging
import string
import time
import urllib2
import base64

from valid.valid_connection import ValidConnection, Expect

from boto import ec2

def randString(length=32):
    return ''.join(random.choice(string.ascii_lowercase) for x in range(length))


argparser = argparse.ArgumentParser(description='Copy amis, update data')
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
argparser.add_argument('--maxtries', type=int,
                       default=30, help='maximum number of tries')
argparser.add_argument('--settlewait', type=int,
                       default=30, help='wait for instance to settle before testing')

argparser.add_argument(
    'data',
    type=argparse.FileType('rw'),
    help='data file to use'
)

operation = argparser.add_mutually_exclusive_group()
operation.add_argument('--clean', action='store_true',
                      help="read data and terminate ami copies found")
operation.add_argument('--check', action='store_true',
                      help="read data and try ami copies found")
operation.add_argument('--copy', action='store_true',
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
    start_thread_ratio = 1.66
    stop_thread_ratio = 3.00

    def run(self):
        while True:
            logging.debug(self.getName() + ": task queue: %s" %yaml.dump(mainq.queue))
            # Thread / queue ratio management
            if mainq.empty() or threading.active_count() / mainq.qsize() > self.stop_thread_ratio:
                if not hasattr(self, "dying"):
                    self.dying = 0
                if self.dying >= 5:
                    # too many retries with stop_thread_ratio reached
                    # terminating
                    logging.debug(self.getName() + ": too sad a queue...")
                    break
                self.dying += 1
                time.sleep(random.randint(2, 12 - 2*self.dying))
                continue
            if threading.active_count() / mainq.qsize() < self.start_thread_ratio:
                logging.debug(self.getName() + ": merry queue...")
                i = InstanceThread()
                i.start()
            self.dying = 0

            try:
                (ntry, action, params) = mainq.get()
                mainq.task_done()
                logging.debug(self.getName() + ": got task: action: (%s, %s, %s)" % (ntry, action, params))
            except Exception as e:
                logging.debug(self.getName() + ": got %s: fetching action; reschedule" % e)
                continue

            if ntry > maxtries:
                logging.error(self.getName() + ": %s: %s failed after %d tries" %
                             (action, params, ntry))
                continue
            if action == 'instantiate':
                self.instantiate(ntry, params)
                continue
            if action == 'connect':
                self.connect(ntry, params)
                continue
            if action == 'take_snapshot':
                self.take_snapshot(ntry, params)
                continue
            if action == 'check_snapshot':
                self.check_snapshot(ntry, params)
                continue
            if action == 'copy_ami':
                self.copy_ami(ntry, params)
                continue
            if action == 'check_copy':
                self.check_copy(ntry, params)
                continue
            if action == 'terminate_dummy':
                self.terminate_dummy(ntry, params)
                continue
            if action == 'remove_snapshot':
                self.remove_snapshot(ntry, params)
                continue
            if action == 'remove_copy_ami':
                self.remove_copy_ami(ntry, params)
                continue

            raise Exception("INTERNAL: action %s unknown" % action)

    def instantiate(self, ntry, params):
        logging.debug(str((ntry, params)))
        ami = params['ami']
        region = ami['region'][0]
        task = None
        
        try:
            region = boto.ec2.get_region(
                region,
                aws_access_key_id=ec2_key,
                aws_secret_access_key=ec2_secret_key
            )

            region_connection = region.connect(
                aws_access_key_id=ec2_key,
                aws_secret_access_key=ec2_secret_key
            )
            if 'snapshot' in ami:
                mainq.put((0, 'check_snapshot', ami.copy()))
                return
            reservation_list = []
            if 'dummy' in ami:
                # already instantiated ??
                reservation_list = region_connection.get_all_instances(
                    instance_ids=ami['dummy']
                )
            if 'dummy' not in ami or not reservation_list:
                reservation_list.append(region_connection.run_instances(
                    ami['ami'],
                    instance_type="m1.small",
                    key_name=params['key_name'],
                    security_groups=['default',]
                ))
            instance = reservation_list[0].instances[0] 
            if instance.update() == 'stopped':
                # go for the taking snapshot??
                # start??
                instance.start()
            count = 0
            while instance.update() == 'pending' and count < maxwait / 5:
                # waiting out instance to appear
                logging.info(self.getName() + ": dummy instance for %s pending; %d" %
                        (ami, maxwait / 5 - count))
                count += 1
                time.sleep(5)
            region_connection.close()
            if instance.update() != 'running':
                raise InstantiationError(
                    "failed to instantiate dummy instance for %s" % ami 
                )
            instance.add_tag("Name", "%s_dummy_%s" % (ami['ami'], randString()))
            ami['dummy'] = instance.id
        except boto.exception.EC2ResponseError as e:
            logging.debug(self.getName() + ": got %s" % e)
            if "<Code>InstanceLimitExceeded</Code>" in str(e):
                logging.info(self.getName() + ": Instance limit reached in %s" % region_name)
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
                logging.info(self.getName() + ": got %s" % e)
                task = (ntry * 1.66 + 1, 'instantiate', params.copy())
        else:
            # it worked!
            logging.info(self.getName() + ": created dummy: %s, %s" %
                        (ami, instance.id))
            task = (0,
                'connect',
                {
                    'ami': ami.copy(),
                    'key_name': params['key_name'],
                    'key_file': params['key_file']
                }
            )
        finally:
            if task is not None:
                logging.debug(self.getName() + ": scheduling: %s" % str(task))
                self.update_data_file_record(ami)
                mainq.put(task)

    def connect(self, ntry, params):
        ami = params['ami']
        key_name = params['key_name']
        key_file = params['key_file']
        count = 0
        try:
            region = boto.ec2.get_region(
                ami['region'][0],
                aws_access_key_id=ec2_key,
                aws_secret_access_key=ec2_secret_key
            )
            region_connection = region.connect(
                aws_access_key_id=ec2_key,
                aws_secret_access_key=ec2_secret_key
            )
            instance = region_connection.get_all_instances(
                instance_ids=ami['dummy']
            )[0].instances[0].__dict__
        except Exception as e:
            logging.warning(self.getName() + ": got %s fetching dummy instance for ami: %s" %
                           (e, ami))
            return
        while count < maxwait / 5 :
            count += 1
            logging.info(self.getName() + ": connecting dummy %s (%d)" %
                        (instance, maxwait / 5 - count))
            logging.debug(self.getName() + ":   key name: %s, key file: %s" % (key_name, key_file))

            con = None
            for user in ['ec2-user', 'cloud-user', 'fedora' ,'root']:
                try:
                    con = ValidConnection(instance, user, key_file)
                    # update client packages
                    #if ami['product'].upper().startswith('RHEL'):
                    #    Expect.expect_retval(con, "yum update rh-amazon-rhui-client", timeout=600) 
                except Exception as e:
                    logging.debug(self.getName() + ": trying user %s: %s" % (user, e))
            if con is not None:
                break
            time.sleep(5)
        if count >= maxwait / 5:
            logging.warning(self.getName() + ": dummy %s: %s not running" %
                          (ami['ami'], ami['dummy']))
        task = (
            0,
            'take_snapshot',
            ami.copy()
            )
        mainq.put(task) 

    def take_snapshot(self, ntry, ami):
        try:
            region = boto.ec2.get_region(
                ami['region'][0],
                aws_access_key_id=ec2_key,
                aws_secret_access_key=ec2_secret_key
            )
            region_connection = region.connect(
                aws_access_key_id=ec2_key,
                aws_secret_access_key=ec2_secret_key
            )

            if 'snapshot' in ami:
                # anything todo?
                    # all done; schedule snapshot check
                    task = (
                        0,
                        'check_snapshot',
                        ami.copy()
                    )
                    mainq.put(task)
                    return

            # stop the instance for snap-shotting
            instance = ami['dummy']
            region_connection.stop_instances(
                instance_ids=[instance]
            )
            instance = region_connection.get_all_instances(
                instance_ids=[instance]
            )[0].instances[0]

            logging.info(self.getName() + ": stopping %s" % ami['dummy'])
    
            results = region_connection.get_all_instances(instance_ids=[ami['dummy']])
            if not results:
                # inconsistent data??
                logging.warning(self.getName() + ": couldn't find dummy in EC2: %s" % ami)
                return

            instance = results[0].instances[0]
            count = 0
            while instance.update() != 'stopped' and count < maxwait / 5:
                # waiting out instance to stop
                logging.info(self.getName() + ": dummy %s stop pending; %d" %
                        (ami['dummy'], maxwait / 5 - count))
                count += 1
                time.sleep(5)
            if instance.update() != 'stopped':
                logging.warning(self.getName() + ": could not stop instance: %s" %
                               ami['dummy'])
                return

            # snapshot the instance ami
            logging.info(self.getName() + ": creating snapshot of %s" % ami['ami'])
            ami['snapshot'] = instance.create_image(
                "ami-snapshot---%s---%s" % (ami['ami'], randString(8)),
                description="a snapshot ami"
            )
            self.update_data_file_record(ami)
            logging.info(self.getName() + ": snapshot %(ami)s: %(dummy)s -> %(snapshot)s taken" % ami)

        except None as e:
            logging.warning(self.getName() + ": got %s taking snapshot: %s" %
                           (e, ami))
            return
        task = (0, 'check_snapshot', ami.copy())
        mainq.put(task) 
        
    def check_snapshot(self, ntry, ami):
        try:
            region = boto.ec2.get_region(
                ami['region'][0],
                aws_access_key_id=ec2_key,
                aws_secret_access_key=ec2_secret_key
            )
            region_connection = region.connect(
                aws_access_key_id=ec2_key,
                aws_secret_access_key=ec2_secret_key
            )

            # wait till the snapshot is taken
            results = region_connection.get_all_images(image_ids=[ami['snapshot']])
            if not results: 
                # inconsistent data??
                logging.warning(self.getName() + ": ami snapshot field present in %s but not found in EC2" % ami)
                return

            snapshot = results[0]
            if snapshot.update(validate=True) != 'available' and ntry < maxtries:
                # reschedule
                logging.info(self.getName() + "%(ami)s: %(dummy)s -> %(snapshot)s: snapshot pending" % ami)
                time.sleep(1)
                mainq.put((ntry + 1, 'check_snapshot', ami.copy()))
                return
                
            if snapshot.update(validate=True) != 'available':
                logging.warning(self.getName() + ": couldn't check snapshot of %s was available in time" % ami)

        except None as e:
            logging.warning(self.getName() + ": got %s checking snapshot: %s" %
                           (e, ami))
            return

        # schedule dummy termination
        task = (
            0,
            "terminate_dummy",
            ami.copy()
        )
        mainq.put(task)

        # schedule all regions copying
        src_region = ami['region'][0]
        for dest_region in ami['region'][1:]:
            ami_copy = ami.copy()
            # region won't be a list anymore
            ami_copy['region'] = dest_region
            task = (0, 'copy_ami', (ami_copy, src_region))
            mainq.put(task) 
        # prevent copying again
        # region not a list anymore
        ami['region'] = src_region
        self.update_data_file_record(ami)

    def copy_ami(self, ntry, params):
        ami = params[0]
        src_region = params[1]
        ami_copy_name = "ami-copy---%s---%s---%s---%s" % (
                ami['region'],
                ami['ami'],
                ami['snapshot'],
                randString(8)
        )
        try:
            region = boto.ec2.get_region(
                ami['region'],
                aws_access_key_id=ec2_key,
                aws_secret_access_key=ec2_secret_key
            )
            
            region_connection = region.connect(
                aws_access_key_id=ec2_key,
                aws_secret_access_key=ec2_secret_key
            )

            logging.info(self.getName() + ": copying %s" % ami_copy_name)
            ami_copy = region_connection.copy_image(
                src_region,
                ami['snapshot'],
                ami_copy_name
            )

            # the ami copy reuses original one save for fields:
            #   ami, copy_of, region 
            ami['copy_of'] = ami['ami']
            ami['ami'] = ami_copy.image_id

            # snapshot is valid just for the 'parent' image; removing for doughter
            del(ami['snapshot'])

            # schedule copy progress check
            mainq.put((0, 'check_copy', ami.copy()))

        except None as e:
            logging.warning(self.getName() + ": got %s creating copy %s" % (e, ami_copy_name))

    def check_copy(self, ntry, ami):
        try:
            region = boto.ec2.get_region(
                ami['region'],
                aws_access_key_id=ec2_key,
                aws_secret_access_key=ec2_secret_key
            )
            
            region_connection = region.connect(
                aws_access_key_id=ec2_key,
                aws_secret_access_key=ec2_secret_key
            )

            logging.info(self.getName() + ": checking %s" % ami['ami'])
            
            results = region_connection.get_all_images(image_ids=[ami['ami']])
            if not results:
                # inconsistent data??
                logging.warning(self.getName() + ": got ami copy: %s but not found in EC2" % ami)
                return

            copy = results[0]
            if copy.update(validate=True) != 'available' and ntry < maxtries:
                # reschedule
                logging.info(self.getName() + "%s: copy pending" % ami['ami'])
                time.sleep(10)
                mainq.put((ntry + 0.2, 'check_copy', ami.copy()))
                return

            if copy.update(validate=True) != 'available':
                logging.warning(self.getName() + ": couldn't copy %s in time" % ami_copy_id)
                return

            self.append_data_file_record(ami)
            logging.info(self.getName() + ": done copying %s" % ami['ami'])

        except None as e:
            logging.warning(self.getName() + ": got %s copying %s" % (e, ami_copy_name))
        
             
    def terminate_dummy(self, ntry, ami): 
        # terminate the dummy instance
        try:
            if not 'dummy' in ami:
                logging.info(self.getName() + ": terminate dummy not needed for %s" % ami)
                return
            region = boto.ec2.get_region(
                ami['region'][0],
                aws_access_key_id=ec2_key,
                aws_secret_access_key=ec2_secret_key
            )
            region_connection = region.connect(
                aws_access_key_id=ec2_key,
                aws_secret_access_key=ec2_secret_key
            )
            results = region_connection.get_all_instances(instance_ids=[ami['dummy']])

            if not results:
                logging.warning(self.getName() + ": got non-existing dummy id: %s" % ami['dummy']) 
                return

            instance = results[0].instances[0]
            logging.info(self.getName() + ": terminating %s" % ami['dummy'])
            instance.terminate()
            count = 0
            while instance.update() != 'terminated' and count < maxwait / 5:
                # waiting out instance to stop
                logging.info(self.getName() + ": dummy %s termination pending; %d" %
                        (ami['dummy'], maxwait / 5 - count))
                count += 1
                time.sleep(5)
            if instance.update() != 'terminated':
                logging.warning(self.getName() + ": could not terminate instance: %s" %
                               ami['dummy'])
                return
            del(ami['dummy'])
            self.update_data_file_record(ami)
            
        except Exception as e:
            logging.warning(self.getName() + ": got %s terminating %s" % (e, ami['dummy']))

    def remove_snapshot(self, ntry, ami):
        try:
            region = boto.ec2.get_region(
                ami['region'],
                aws_access_key_id=ec2_key,
                aws_secret_access_key=ec2_secret_key
            )
            
            region_connection = region.connect(
                aws_access_key_id=ec2_key,
                aws_secret_access_key=ec2_secret_key
            )

            logging.info(self.getName() + ": removing snapshot %s" % ami['snapshot'])
            
            results = region_connection.get_all_images(image_ids=[ami['snapshot']])
            if not results:
                # inconsistent data??
                logging.warning(self.getName() + ": got snapshot: %s but not found in EC2; removing from data" % ami['snapshot'])
                del(ami['snapshot'])
                self.update_data_file_record(ami)
                return

            snapshot = results[0]
            snapshot.deregister(delete_snapshot=True)
            del(ami['snapshot'])
            self.update_data_file_record(ami)

        except None as e:
            logging.warning(self.getName() + ": got %s removing snapshot ami for %s" % (e, ami))
        
    def remove_copy_ami(self, ntry, ami):
        try:
            region = boto.ec2.get_region(
                ami['region'],
                aws_access_key_id=ec2_key,
                aws_secret_access_key=ec2_secret_key
            )
            
            region_connection = region.connect(
                aws_access_key_id=ec2_key,
                aws_secret_access_key=ec2_secret_key
            )

            logging.info(self.getName() + ": removing copy %s" % ami['ami'])
            
            results = region_connection.get_all_images(image_ids=[ami['ami']])
            if not results:
                # inconsistent data??
                logging.warning(self.getName() + ": got copy %s but not found in EC2; removing" % ami['ami'])
                self.remove_data_file_record(ami)
                return

            copy = results[0]
            # TODO: copy.deregister(delete_snapshot=True)
            copy.deregister()
            self.remove_data_file_record(ami)

        except None as e:
            logging.warning(self.getName() + ": got %s removing copy ami %s" % (e, ami))



    def append_data_file_record(self, record):
        with open(args.data.name, "r+") as fd, data_lock:
            data = yaml.load(fd)
            if type(data) is not list:
                raise TypeError("Can't process data file: %s, not a list of items" % args.data.name)

            logging.debug(self.getName() + ": appending record: %s" % record)
            data.append(record)        

            # dump data
            logging.debug(self.getName() + ": dumping: %s" % data)
            try:
                fd.seek(0)
                yaml.dump(data, fd)
                fd.truncate()
            except Exception as e:
                logging.error(self.getName() + ":Couldn't update %s: %s" %
                             (fd.name, e))
            else:
                logging.debug(self.getName() +": written %s" % fd.name)


    def update_data_file_record(self, record):
        with open(args.data.name, "r+") as fd, data_lock:
            data = yaml.load(fd)
            if type(data) is not list:
                raise TypeError("Can't process data file: %s, not a list of items" % args.data.name)

            for i in range(len(data)):
                entry = data[i]
                logging.debug(self.getName() + ": data[%d] == %s" % (i, entry))
                if type(entry) is not dict:
                    logging.debug(self.getName() + ": skip non-dict record: %s" % entry)
                    continue 
                if 'ami' not in entry:
                    logging.debug(self.getName() + ": skip non-ami record: %s" % entry)
                    continue
                if entry['ami'] == record['ami']:
                    logging.debug(self.getName() + ": updating %s -> %s" % (entry, record))
                    data[i] = record
    
            # dump data
            logging.debug(self.getName() + ": dumping: %s" % data)
            try:
                fd.seek(0)
                yaml.dump(data, fd)
                fd.truncate()
            except Exception as e:
                logging.error(self.getName() + ":Couldn't update %s: %s" %
                             (fd.name, e))
            else:
                logging.debug(self.getName() +": written %s" % fd.name)

    def remove_data_file_record(self, record):
        with data_lock, open(args.data.name, "r+") as fd:
            data = yaml.load(fd)
            if type(data) is not list:
                raise TypeError("Can't process data file: %s, not a list of items" % args.data.name)

            for i in range(len(data)):
                entry = data[i]
                logging.debug(self.getName() + ": data[%d] == %s" % (i, entry))
                if type(entry) is not dict:
                    logging.debug(self.getName() + ": skip non-dict record: %s" % entry)
                    continue 
                if 'ami' not in entry:
                    logging.debug(self.getName() + ": skip non-ami record: %s" % entry)
                    continue
                if entry == record:
                    logging.debug(self.getName() + ": deleting record: %s" % record)
                    del(data[i])
                    # fixme; multiple entries won't get deleted this way
                    # but it prevents index out of range errors to terminate the loop here
                    break
                
            # dump data
            logging.debug(self.getName() + ": tell: %d" % fd.tell())
            logging.debug(self.getName() + ": dumping: %s" % data)
            try:
                fd.seek(0)
                yaml.dump(data, fd)
                fd.truncate()
            except None as e:
                logging.error(self.getName() + ":Couldn't update %s: %s" %
                             (fd.name, e))
            else:
                logging.debug(self.getName() +": written %s" % fd.name)


def copy_amis(data, ssh_config, transitive=False):
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
        if type(entry['region']) is not list or len(entry['region']) < 2:
            logging.debug('skipping non-copy-ami entry: %s' % entry)
            continue
        for region in entry['region']:
            if region not in ssh_config:
                print >>sys.stderr, "region %s not configured in %s" % \
                      (entry['region'], args.config.name)
        task = {
            'key_name': ssh_config[entry['region'][0]][0],
            'key_file': ssh_config[entry['region'][0]][1],
            'ami': entry
        }
        logging.info('scheduling task: %s' % str(task))
        mainq.put((0, 'instantiate', task))

def clean_amis(data):
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
        if 'copy_of' in entry:
            mainq.put((0, 'remove_copy_ami', entry.copy()))
            continue
        if 'snapshot' in entry:
            mainq.put((0, 'remove_snapshot', entry.copy()))
            continue

        logging.debug('skipping non-copy/non-snapshot ami: %s' % entry)


if args.copy:
    logging.info("copying amis for %s" % args.data.name)
    copy_amis(data, config['ssh'])

if args.clean:
    logging.info("cleaning amis for %s" % args.data.name)
    clean_amis(data)

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


