import time
import threading
import logging
from valid.valid_testcase import *


class testcase_361_ebs_deferred_detach(ValidTestcase):
    """
    Perform EBS test:
    - Create the volume
    - Attach the volume
    - Use the volume
    - Try to detach the volume
    - Try to umount the volume
    - Remove volume
    """
    stages = ['stage1']
    tags = ['default', 'kernel']

    def test(self, connection, params):
        prod = params['product'].upper()
        ver = params['version'].upper()
        device = '/dev/sdk'
        if params['ec2name'] == 'hs1.8xlarge':
            for dev in params['bmap']:
                if dev['name'] == device:
                    device = '/dev/xvdac'
                    break
        ec2connection = params['instance']['connection']
        if 'placement' in params['instance']:
            volume = ec2connection.create_volume(3, params['instance']['placement'])
        elif '_placement' in params['instance']:
            volume = ec2connection.create_volume(3, params['instance']['_placement'])
        else:
            self.log.append({'result': 'failure',
                             'comment': 'Failed to get instance placement'
                             })
            return self.log
        logging.debug(threading.currentThread().name + ': Volume %s created' % volume.id)
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
            logging.debug(threading.currentThread().name + ': Ready to attach %s: %s %s' % (volume.id, volume.volume_state(), volume.attachment_state()))
            ec2connection.attach_volume(volume.id, params['instance']['id'], device)
            time.sleep(5)
            volume.update()
            wait = 0
            while volume.attachment_state() == 'attaching':
                volume.update()
                logging.debug(threading.currentThread().name + ': Wait attaching %s: %s %s' % (volume.id, volume.volume_state(), volume.attachment_state()))
                time.sleep(1)
                wait += 1
                if wait > 300:
                    self.log.append({'result': 'failure',
                                     'comment': 'Failed to attach EBS volume %s (timeout 300)' % volume.id
                                     })
                    ec2connection.delete_volume(volume.id)
                    return self.log
            if volume.attachment_state() != 'attached':
                logging.debug(threading.currentThread().name + ': Error attaching volume %s' % volume.id)
                self.log.append({'result': 'failure',
                                 'comment': 'Failed to attach EBS volume %s' % volume.id
                                 })
                ec2connection.delete_volume(volume.id)
                return self.log

            if (prod in ['RHEL', 'BETA']) and (ver.startswith('5.')):
                name = device
            elif (prod in ['RHEL', 'BETA']) and (ver.startswith('6.')) and (params['virtualization'] != 'hvm'):
                # 4-letter shift
                name = device.replace("/dev/sd", "/dev/xvd")[:-1] + chr(ord(device.replace("/dev/sd", "/dev/xvd")[-1:]) + 4)
            else:
                name = device.replace("/dev/sd", "/dev/xvd")
            # waiting for this volume
            for i in range(20):
                if self.get_return_value(connection, 'ls -l %s' % name, 30, nolog=True) == 0:
                    break
                time.sleep(1)
            self.get_return_value(connection, 'ls -l %s' % name, 30)
            self.get_return_value(connection, 'echo y| mkfs.ext3 %s' % name, 300)

            self.get_return_value(connection, 'mkdir /mnt/deferred')
            self.get_return_value(connection, 'mount %s /mnt/deferred' % name)
            self.get_return_value(connection, 'dd if=/dev/zero of=/mnt/deferred/zzz_file bs=512 count=102400')

            logging.debug(threading.currentThread().name + ': Ready to detach %s: %s %s' % (volume.id, volume.volume_state(), volume.attachment_state()))
            ec2connection.detach_volume(volume.id)
            time.sleep(20)
            volume.update()

            if self.get_return_value(connection, 'umount /mnt/deferred', 20) is None:
                # bug#794803
                # doing force-detach
                ec2connection.detach_volume(volume.id, force=True)

            wait = 0
            while volume.attachment_state() == 'detaching':
                volume.update()
                logging.debug(threading.currentThread().name + ': Wait detaching %s: %s %s' % (volume.id, volume.volume_state(), volume.attachment_state()))
                time.sleep(1)
                wait += 1
                if wait > 300:
                    self.log.append({'result': 'failure',
                                     'comment': 'Failed to detach EBS volume %s (timeout 300)' % volume.id
                                     })
                    ec2connection.delete_volume(volume.id)
                    return self.log
            if volume.volume_state() != 'available':
                logging.debug(threading.currentThread().name + ': Error detaching volume %s' % volume.id)
                self.log.append({'result': 'failure',
                                 'comment': 'Failed to detach EBS volume %s' % volume.id
                                 })
                return self.log
            logging.debug(threading.currentThread().name + ': Ready to delete %s: %s %s' % (volume.id, volume.volume_state(), volume.attachment_state()))
            if not ec2connection.delete_volume(volume.id):
                self.log.append({'result': 'failure',
                                 'comment': 'Failed to remove EBS volume %s' % volume.id
                                 })
        else:
            self.log.append({'result': 'failure',
                             'comment': 'Failed to create EBS volume %s' % volume.id
                             })
        return self.log
