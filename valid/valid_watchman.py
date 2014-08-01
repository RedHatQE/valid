"""
validation worker's watcher process module
"""


import multiprocessing
import logging
from valid.logging_customizations import ValidLogger
logging.setLoggerClass(ValidLogger)
import time
import random
import yaml
import smtplib

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from valid import valid_result, valid_worker
from fractions import Fraction


class WatchmanProcess(multiprocessing.Process):
    """
    Special Process to watch over other Processes:
    - Create WorkerProcesses when we have long queue
    - report result for a transaction when it's ready
    """
    def __init__(self, shareddata):
        """
        Create WatchmanProcess object
        """
        self.shareddata = None
        multiprocessing.Process.__init__(self, name='WatchmanProcess', target=self.runner, args=(shareddata,))
        self.logger = logging.getLogger('valid.runner')


    def runner(self, shareddata):
        """
        Run process
        """
        self.shareddata = shareddata
        while True:
            self.logger.debug('WatchmanProcess: heartbeat numprocesses: %i', shareddata.numprocesses.value)
            time.sleep(random.randint(2, 10))
            self.report_results()
            # FIXME: self.add_worker_processes()
            if shareddata.resultdic.keys() == [] and shareddata.time2die.get():
                break

    def add_worker_processes(self):
        """
        Create additional worker processes when something has to be done
        """
        processes_2create = min(self.shareddata.maxprocesses - self.shareddata.numprocesses.value, self.shareddata.mainq.qsize())
        if processes_2create > 0:
            self.logger.debug('WatchmanProcess: should create %i additional worker processes', processes_2create)
            for _ in range(processes_2create):
                workprocess = valid_worker.WorkerProcess(self.shareddata)
                with self.shareddata.numprocesses_lock:
                    self.shareddata.numprocesses.value += 1
                workprocess.start()

    def transaction_progress(self, transaction_id, transaction_dict):
        """
        return the progress of a transaction in the form of a fraction
        return type Fraction
        """
        tasks_total_count = sum([int(transaction_dict[ami]['ninstances']) for ami in transaction_dict])
        tasks_finished_count = sum([len(transaction_dict[ami]['instances']) for ami in transaction_dict])
        ret = Fraction(tasks_finished_count, tasks_total_count)
        # pylint: disable=maybe-no-member
        self.logger.progress("%s: %.2f%% (%s/%s)", transaction_id, 100*ret, tasks_finished_count, tasks_total_count)
        return ret

    def report_results(self):
        """
        Looking if we can report some transactions
        """
        with self.shareddata.resultdic_lock:
            for transaction_id in self.shareddata.resultdic.keys():
                # Checking all transactions
                transaction_dict = self.shareddata.resultdic[transaction_id].copy()
                # if the transaction progress ratio is equal to 1.0 the transaction is finished
                if self.transaction_progress(transaction_id, transaction_dict) == 1.0:
                    resfile = self.shareddata.resdir + '/' + transaction_id + '.yaml'
                    result = []
                    data = transaction_dict
                    emails = None
                    subject = None
                    for ami in data.keys():
                        result_item = {'ami': data[ami]['instances'][0]['ami'],
                                       'product': data[ami]['instances'][0]['product'],
                                       'version': data[ami]['instances'][0]['version'],
                                       'arch': data[ami]['instances'][0]['arch'],
                                       'region': data[ami]['instances'][0]['region'],
                                       'console_output': {},
                                       'result': {}}
                        for instance in data[ami]['instances']:
                            if not instance['instance_type'] in result_item['result'].keys():
                                result_item['result'][instance['instance_type']] = instance['result'].copy()
                            else:
                                result_item['result'][instance['instance_type']].update(instance['result'])
                            # we're interested in latest console output only, overwriting
                            result_item['console_output'][instance['instance_type']] = instance['console_output']
                        result.append(result_item)
                        # setting shareddata.last_testing_exitstatus, valid_runner script will return this exit status
                        overall_result, _, _, _ = valid_result.get_overall_result(result_item)
                        if overall_result == 'succeeded':
                            self.shareddata.last_testing_exitstatus.set(0)
                        else:
                            self.shareddata.last_testing_exitstatus.set(1)
                        if 'emails' in data[ami].keys():
                            emails = data[ami]['emails']
                        if 'subject' in data[ami].keys():
                            subject = data[ami]['subject']
                    result_yaml = yaml.safe_dump(result)
                    self.shareddata.resultdic_yaml[transaction_id] = result_yaml
                    try:
                        result_fd = open(resfile, 'w')
                        result_fd.write(result_yaml)
                        result_fd.close()
                        if emails:
                            for ami in result:
                                overall_result, bug_summary, bug_description = valid_result.get_overall_result(ami)
                                msg = MIMEMultipart()
                                msg.preamble = 'Validation result'
                                if subject:
                                    msg['Subject'] = "[" + overall_result + "] " + subject
                                else:
                                    msg['Subject'] = "[" + overall_result + "] " + bug_summary
                                msg['From'] = self.shareddata.mailfrom
                                msg['To'] = emails
                                txt = MIMEText(bug_description + '\n')
                                msg.attach(txt)
                                txt = MIMEText(yaml.safe_dump(ami), 'yaml')
                                msg.attach(txt)
                                smtp = smtplib.SMTP('localhost')
                                smtp.sendmail(self.shareddata.mailfrom, emails.split(','), msg.as_string())
                                smtp.quit()
                    # pylint: disable=broad-except
                    except Exception, err:
                        self.logger.error('WatchmanProcess: saving result failed, %s', err)
                    # pylint: disable=maybe-no-member
                    self.logger.progress('Transaction ' + transaction_id + ' finished. Result: ' + resfile)
                    self.shareddata.resultdic.pop(transaction_id)
