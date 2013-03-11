import time
import threading
import logging
from valid.valid_testcase import *


class testcase_36_ebs(ValidTestcase):
    stages = ["stage1"]
    tags = ["default", "kernel"]

    def test(self, connection, params):
        prod = params["product"].upper()
        ver = params["version"].upper()
        ec2connection = params["instance"]["connection"]
        if "placement" in params["instance"]:
            volume = ec2connection.create_volume(10, params["instance"]["placement"])
        elif "_placement" in params["instance"]:
            volume = ec2connection.create_volume(10, params["instance"]["_placement"])
        else:
            self.log.append({
                    "result": "failure",
                    "comment": "Failed to get instance placement"
                    })
            return self.log
        logging.debug(threading.currentThread().name + ": Volume %s created" % volume.id)
        time.sleep(5)
        volume.update()
        wait = 0
        while volume.volume_state() == "creating":
            time.sleep(1)
            wait += 1
            if wait > 300:
                self.log.append({
                        "result": "failure",
                        "comment": "Failed to create EBS volume %s (timeout 300)" % volume.id
                        })
                ec2connection.delete_volume(volume.id)
                return self.log
        if volume.volume_state() == "available":
            logging.debug(threading.currentThread().name + ": Ready to attach %s: %s %s" % (volume.id, volume.volume_state(), volume.attachment_state()))
            ec2connection.attach_volume(volume.id, params["instance"]["id"], "/dev/sdk")
            time.sleep(5)
            volume.update()
            wait = 0
            while volume.attachment_state() == "attaching":
                volume.update()
                logging.debug(threading.currentThread().name + ": Wait attaching %s: %s %s" % (volume.id, volume.volume_state(), volume.attachment_state()))
                time.sleep(1)
                wait += 1
                if wait > 300:
                    self.log.append({
                            "result": "failure",
                            "comment": "Failed to attach EBS volume %s (timeout 300)" % volume.id
                            })
                    ec2connection.delete_volume(volume.id)
                    return self.log
            if volume.attachment_state() != "attached":
                logging.debug(threading.currentThread().name + ": Error attaching volume %s" % volume.id)
                self.log.append({
                        "result": "failure",
                        "comment": "Failed to attach EBS volume %s" % volume.id
                        })
                ec2connection.delete_volume(volume.id)
                return self.log

            if (prod in ["RHEL", "BETA"]) and (ver.startswith("5.")):
                name = "/dev/sdk"
            else:
                name = "/dev/xvdk"
            # waiting for this volume
            for i in range(20):
                if self.get_return_value(connection, "ls -l %s" % name, 30, nolog=True) == 0:
                    break
                time.sleep(1)
            self.get_return_value(connection, "ls -l %s" % name, 30)
            if self.get_result(connection, "ls -la /sbin/mkfs.vfat 2> /dev/null | wc -l", 5) == "1":
                # mkfs.vfat is faster!
                self.get_return_value(connection, "mkfs.vfat -I %s" % name, 60)
            else:
                self.get_return_value(connection, "mkfs.ext3 %s" % name, 300)
            logging.debug(threading.currentThread().name + ": Ready to detach %s: %s %s" % (volume.id, volume.volume_state(), volume.attachment_state()))
            ec2connection.detach_volume(volume.id)
            time.sleep(5)
            volume.update()
            wait = 0
            while volume.attachment_state() == "detaching":
                volume.update()
                logging.debug(threading.currentThread().name + ": Wait detaching %s: %s %s" % (volume.id, volume.volume_state(), volume.attachment_state()))
                time.sleep(1)
                wait += 1
                if wait > 300:
                    self.log.append({
                            "result": "failure",
                            "comment": "Failed to detach EBS volume %s (timeout 300)" % volume.id
                            })
                    ec2connection.delete_volume(volume.id)
                    return self.log
            if volume.volume_state() != "available":
                logging.debug(threading.currentThread().name + ": Error detaching volume %s" % volume.id)
                self.log.append({
                        "result": "failure",
                        "comment": "Failed to attach EBS volume %s" % volume.id
                        })
                return self.log
            logging.debug(threading.currentThread().name + ": Ready to delete %s: %s %s" % (volume.id, volume.volume_state(), volume.attachment_state()))
            if not ec2connection.delete_volume(volume.id):
                self.log.append({
                        "result": "failure",
                        "comment": "Failed to remove EBS volume %s" % volume.id
                        })
        else:
            self.log.append({
                    "result": "failure",
                    "comment": "Failed to create EBS volume %s" % volume.id
                    })
        return self.log
