import time
import multiprocessing
import logging
from valid.valid_testcase import *


class testcase_360_ebs(ValidTestcase):
    """
    Perform EBS test:
    - Create the volume
    - Attach the volume
    - Try to use the volume
    - Detach the volume
    - Remove volume
    """
    stages = ['stage1']
    tags = ['default', 'kernel']
    not_applicable = {"product": "(?i)RHEL|BETA", "version": "6.0"}

    def test(self, connection, params):
        prod = params['product'].upper()
        ver = params['version'].upper()
        device = '/dev/sdk'
        device_modified = True
        while device_modified:
            # searching for free device
            device_modified = False
            for dev in params['bmap']:
                if dev['name'] == device:
                    device_modified = True
                    device = device[:-1] + chr(ord(device[-1:]) + 1)
                    if device == '/dev/sdz':
                        # hs1.8xlarge possibly
                        device = '/dev/xvdaa'
        ec2connection = params['instance']['connection']
        if 'placement' in params['instance']:
            volume = ec2connection.create_volume(10, params['instance']['placement'])
        elif '_placement' in params['instance']:
            volume = ec2connection.create_volume(10, params['instance']['_placement'])
        else:
            self.log.append({'result': 'failure',
                             'comment': 'Failed to get instance placement'
                             })
            return self.log
        logging.debug(multiprocessing.current_process().name + ': Volume %s created' % volume.id)
        time.sleep(5)
        volume.update()
        wait = 0
        while volume.volume_state() == 'creating':
            time.sleep(1)
            wait += 1
            if wait > 300:
                self.log.append({'result': 'failure',
                                 'comment': 'Failed to create EBS volume %s (timeout 300)' % volume.id
                                 })
                ec2connection.delete_volume(volume.id)
                return self.log
        if volume.volume_state() == 'available':
            logging.debug(multiprocessing.current_process().name + ': Ready to attach %s: %s %s' % (volume.id, volume.volume_state(), volume.attachment_state()))
            ec2connection.attach_volume(volume.id, params['instance']['id'], device)
            time.sleep(5)
            volume.update()
            wait = 0
            while volume.attachment_state() == 'attaching':
                volume.update()
                logging.debug(multiprocessing.current_process().name + ': Wait attaching %s: %s %s' % (volume.id, volume.volume_state(), volume.attachment_state()))
                time.sleep(1)
                wait += 1
                if wait > 300:
                    self.log.append({'result': 'failure',
                                     'comment': 'Failed to attach EBS volume %s (timeout 300)' % volume.id
                                     })
                    ec2connection.delete_volume(volume.id)
                    return self.log
            if volume.attachment_state() != 'attached':
                logging.debug(multiprocessing.current_process().name + ': Error attaching volume %s' % volume.id)
                self.log.append({'result': 'failure',
                                 'comment': 'Failed to attach EBS volume %s' % volume.id
                                 })
                ec2connection.delete_volume(volume.id)
                return self.log

            if (prod in ['RHEL', 'BETA']) and (ver.startswith('5.')):
                name = device
            elif (prod in ['RHEL', 'BETA']) and ver in ['6.1', '6.2', '6.3', '6.4'] and (params['virtualization'] != 'hvm'):
                # 4 letter shift
                name = device.replace("/dev/sd", "/dev/xvd")[:-1] + chr(ord(device.replace("/dev/sd", "/dev/xvd")[-1:]) + 4)
            else:
                name = device.replace("/dev/sd", "/dev/xvd")
            # waiting for this volume
            for i in range(20):
                if self.get_return_value(connection, 'ls -l %s' % name, 30, nolog=True) == 0:
                    break
                time.sleep(1)
            self.get_return_value(connection, 'ls -l %s' % name, 30)
            if self.get_result(connection, 'ls -la /sbin/mkfs.vfat 2> /dev/null | wc -l', 5) == '1':
                # mkfs.vfat is faster!
                self.get_return_value(connection, 'mkfs.vfat -I %s' % name, 60)
            else:
                self.get_return_value(connection, 'echo y | mkfs.ext3 %s' % name, 300)
            logging.debug(multiprocessing.current_process().name + ': Ready to detach %s: %s %s' % (volume.id, volume.volume_state(), volume.attachment_state()))
            ec2connection.detach_volume(volume.id)
            time.sleep(5)
            volume.update()
            wait = 0
            while volume.attachment_state() == 'detaching':
                volume.update()
                logging.debug(multiprocessing.current_process().name + ': Wait detaching %s: %s %s' % (volume.id, volume.volume_state(), volume.attachment_state()))
                time.sleep(1)
                wait += 1
                if wait > 300:
                    self.log.append({'result': 'failure',
                                     'comment': 'Failed to detach EBS volume %s (timeout 300)' % volume.id
                                     })
                    ec2connection.delete_volume(volume.id)
                    return self.log
            if volume.volume_state() != 'available':
                logging.debug(multiprocessing.current_process().name + ': Error detaching volume %s' % volume.id)
                self.log.append({'result': 'failure',
                                 'comment': 'Failed to detach EBS volume %s' % volume.id
                                 })
                return self.log
            logging.debug(multiprocessing.current_process().name + ': Ready to delete %s: %s %s' % (volume.id, volume.volume_state(), volume.attachment_state()))
            if not ec2connection.delete_volume(volume.id):
                self.log.append({'result': 'failure',
                                 'comment': 'Failed to remove EBS volume %s' % volume.id
                                 })
        else:
            self.log.append({'result': 'failure',
                             'comment': 'Failed to create EBS volume %s' % volume.id
                             })
        return self.log
