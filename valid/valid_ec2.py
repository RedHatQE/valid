import boto
import logging

from boto.ec2.blockdevicemapping import BlockDeviceType
from boto.ec2.blockdevicemapping import BlockDeviceMapping

def get_connection(params):
    ec2_key, ec2_secret_key = params['credentials']
    reg = boto.ec2.get_region(params['region'], aws_access_key_id=ec2_key, aws_secret_access_key=ec2_secret_key)
    connection = reg.connect(aws_access_key_id=ec2_key, aws_secret_access_key=ec2_secret_key)
    return connection

def get_bmap(params):
    logger = logging.getLogger('valid.runner')
    bmap = BlockDeviceMapping()
    for device in params['bmap']:
        if not 'name' in device.keys():
            logger.debug('bad device ' + str(device))
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

def get_console_output(params):
    connection = get_connection(params)
    return connection.get_console_output(params['id']).output

