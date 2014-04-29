import boto
import logging
import traceback
import socket
import time

from boto.ec2.blockdevicemapping import BlockDeviceType
from boto.ec2.blockdevicemapping import BlockDeviceMapping

from valid.cloud.base import *

class OpenStackEC2(AbstractCloud):
    """
    OpenStack driver using EC2 API emulation
    """
    cloud = 'openstack'
    mandatory_fields = []

    def __init__(self, logger, maxwait):
        AbstractCloud.__init__(self, logger, maxwait)
        logging.getLogger('boto').setLevel(logging.CRITICAL)

    def set_default_params(self, params, cloud_access_config):
        try:
            if not 'bmap' in params:
                params['bmap'] = [{'name': '/dev/sda1', 'size': '15', 'delete_on_termination': True}]
            if not 'userdata' in params:
                params['userdata'] = None
            params['credentials'] = {'ec2_access_key': cloud_access_config[self.cloud]['ec2_access_key'],
                                     'ec2_secret_key': cloud_access_config[self.cloud]['ec2_secret_key'],
                                     'port': cloud_access_config[self.cloud]['port'],
                                     'endpoint': cloud_access_config[self.cloud]['endpoint'],
                                     'path': cloud_access_config[self.cloud]['path']}

            params['ssh'] = {'keypair': cloud_access_config[self.cloud]['ssh'][0],
                             'keyfile': cloud_access_config[self.cloud]['ssh'][1]}
        except Exception, err:
            PermanentCloudException('Error while setting up required cloud params: %s' % err)

    def create(self, params):
        try:
            ssh_key_name = params['ssh']['keypair']

            bmap = self._get_bmap(params)
            connection = self._get_connection(params)

            reservation = connection.run_instances(
                params['ami'],
                instance_type=params['cloudhwname'],
                key_name=ssh_key_name,
                block_device_map=bmap,
                subnet_id=params.get('subnet_id'),
                user_data=params.get('userdata')
            )
            myinstance = reservation.instances[0]
            count = 0
            # Sometimes EC2 failes to return something meaningful without small timeout between run_instances() and update()
            time.sleep(10)
            while myinstance.update() == 'pending' and count < self.maxwait / 5:
                # Waiting out instance to appear
                self.logger.debug(params['iname'] + '... waiting...' + str(count))
                time.sleep(5)
                count += 1
            connection.close()
            instance_state = myinstance.update()
            if instance_state == 'running':
                # Instance appeared - scheduling 'setup' stage
                # can't assign tags in openstack
                # myinstance.add_tag('Name', params['name'])
                result = myinstance.__dict__
                self.logger.info('EC2: Created instance ' + params['iname'] + ', ' + result['id'] + ':' + result['public_dns_name'])
                # packing creation results into params
                params['id'] = result['id']
                params['instance'] = result.copy()
                if result['public_dns_name'] != '':
                    params['hostname'] = result['public_dns_name']
                else:
                    params['hostname'] = result['private_ip_address']
                return params
            elif instance_state == 'pending':
                # maxwait seconds is enough to create an instance. If not -- EC2 failed.
                result = myinstance.__dict__
                if 'id' in result.keys():
                    # terminate stucked instance
                    params['id'] = result['id']
                    params['instance'] = result.copy()
                    self.terminate(params)
                raise UnknownCloudException('Error during instance creation: timeout in pending state')
            else:
                # error occured
                raise UnknownCloudException('Error during instance creation: ' + instance_state)

        except boto.exception.EC2ResponseError, err:
            # Boto errors should be handled according to their error Message - there are some well-known ones
            self.logger.debug('got boto error during instance creation: %s' % err)
            if str(err).find('<Code>InstanceLimitExceeded</Code>') != -1:
                # InstanceLimit is temporary problem
                raise TemporaryCloudException('got InstanceLimitExceeded - not increasing ntry')
            elif str(err).find('<Code>InvalidParameterValue</Code>') != -1:
                # InvalidParameterValue is really bad
                raise PermanentCloudException('got error during instance creation: %s' % err)
            elif str(err).find('<Code>InvalidAMIID.NotFound</Code>') != -1:
                # No such AMI in the region
                raise PermanentCloudException('AMI %s not found' % params['ami'])
            elif str(err).find('<Code>AuthFailure</Code>') != -1:
                # Not authorized is permanent
                raise PermanentCloudException('not authorized for AMI %s' % params['ami'])
            elif str(err).find('<Code>Unsupported</Code>') != -1:
                # Unsupported hardware in the region
                raise SkipCloudException('got Unsupported - most likely the permanent error: %s' % err)
            else:
                raise UnknownCloudException('Unknown boto error during instance creation: ' + traceback.format_exc())
        except socket.error, err:
            # Unexpected error happened
            raise TemporaryCloudException('Socket error during instance creation: ' + traceback.format_exc())
        except Exception, err:
            # Unexpected error happened
            raise UnknownCloudException('Unknown error during instance creation: ' + traceback.format_exc())

    def terminate(self, params):
        try:
            connection = self._get_connection(params)
            res = connection.terminate_instances([params['id']])
        except Exception, err:
            raise UnknownCloudException('Unknown error during instance termination: %s (%s)' % (err, traceback.format_exc()))
        return res

    def get_console_output(self, params):
        connection = self._get_connection(params)
        return connection.get_console_output(params['id']).output

    def _get_connection(self, params):
        ec2_access_key, ec2_secret_key = params['credentials']['ec2_access_key'], params['credentials']['ec2_secret_key']

        region = boto.ec2.regioninfo.RegionInfo(name="os", endpoint=params['credentials']['endpoint'])
        # FIXME: connection is always insecure
        connection = boto.connect_ec2(aws_access_key_id=ec2_access_key,
                                      aws_secret_access_key=ec2_secret_key,
                                      is_secure=False,
                                      region=region,
                                      port=params['credentials']['port'],
                                      path=params['credentials']['path'])
        return connection

    def _get_bmap(self, params):
        bmap = BlockDeviceMapping()
        for device in params['bmap']:
            if not 'name' in device.keys():
                self.logger.debug('bad device ' + str(device))
                continue
            dev = BlockDeviceType()
            if 'size' in device.keys():
                dev.size = device['size']
            if 'delete_on_termination' in device.keys():
                dev.delete_on_termination = device['delete_on_termination']
            if 'ephemeral_name' in device.keys():
                dev.ephemeral_name = device['ephemeral_name']
            bmap[device['name']] = dev
        return bmap
