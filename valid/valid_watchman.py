import multiprocessing
import logging
import time
import random
import yaml
import smtplib

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import valid


class WatchmanProcess(multiprocessing.Process):
    """
    Special Process to watch over other Processes:
    - Create WorkerProcesses when we have long queue
    - report result for a transaction when it's ready
    """
    def __init__(self, *args, **kwargs):
        """
        Create WatchmanProcess object
        """
        multiprocessing.Process.__init__(self, name='WatchmanProcess', target=self.runner, args=args, kwargs=kwargs)
        self.logger = logging.getLogger('valid.runner')

    def runner(self, resultdic, resultdic_lock, resultdic_yaml, mainq, mailfrom, numprocesses, minprocesses, maxprocesses, yamlconfig, settlewait, maxtries, maxwait, httpserver, resdir):
        """
        Run process
        """
        self.resultdic = resultdic
        self.resultdic_lock = resultdic_lock
        self.resultdic_yaml = resultdic_yaml
        self.mainq = mainq
        self.numprocesses = numprocesses
        self.minprocesses = minprocesses
        self.maxprocesses = maxprocesses
        self.yamlconfig = yamlconfig
        self.settlewait = settlewait
        self.maxtries = maxtries
        self.maxwait = maxwait
        self.httpserver = httpserver
        self.mailfrom = mailfrom
        self.resdir = resdir
        
        while True:
            self.logger.debug('WatchmanProcess: heartbeat numprocesses: %i', numprocesses.value)
            time.sleep(random.randint(2, 10))
            self.report_results()
            self.add_worker_processes()
            if resultdic.keys() == [] and not httpserver:
                break

    def add_worker_processes(self):
        """
        Create additional worker processes when something has to be done
        """
        processes_2create = min(self.maxprocesses - self.numprocesses.value, self.mainq.qsize())
        if processes_2create > 0:
            self.logger.debug('WatchmanProcess: should create %i additional worker processes', processes_2create)
            for _ in range(processes_2create):
                workprocess = valid.valid_worker.WorkerProcess(self.resultdic, self.resultdic_lock, self.mainq, self.numprocesses, self.minprocesses, self.yamlconfig, self.settlewait, self.maxtries, self.maxwait, self.httpserver)
                self.numprocesses.value += 1
                workprocess.start()

    def report_results(self):
        """
        Looking if we can report some transactions
        """
        with self.resultdic_lock:
            for transaction_id in self.resultdic.keys():
                # Checking all transactions
                transaction_dict = self.resultdic[transaction_id].copy()
                report_ready = True
                for ami in transaction_dict.keys():
                    # Checking all amis: they should be finished
                    if transaction_dict[ami]['ninstances'] != len(transaction_dict[ami]['instances']):
                        # Still have some jobs running ...
                        self.logger.debug('WatchmanProcess: ' + transaction_id + ': ' + ami + ':  waiting for ' + str(transaction_dict[ami]['ninstances']) + ' results, got ' + str(len(transaction_dict[ami]['instances'])))
                        report_ready = False
                if report_ready:
                    resfile = self.resdir + '/' + transaction_id + '.yaml'
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
                        if 'emails' in data[ami].keys():
                            emails = data[ami]['emails']
                        if 'subject' in data[ami].keys():
                            subject = data[ami]['subject']
                    result_yaml = yaml.safe_dump(result)
                    self.resultdic_yaml[transaction_id] = result_yaml
                    try:
                        result_fd = open(resfile, 'w')
                        result_fd.write(result_yaml)
                        result_fd.close()
                        if emails:
                            for ami in result:
                                overall_result, bug_summary, bug_description = valid.valid_result.get_overall_result(ami)
                                msg = MIMEMultipart()
                                msg.preamble = 'Validation result'
                                if subject:
                                    msg['Subject'] = "[" + overall_result + "] " + subject
                                else:
                                    msg['Subject'] = "[" + overall_result + "] " + bug_summary
                                msg['From'] = self.mailfrom
                                msg['To'] = emails
                                txt = MIMEText(bug_description + '\n')
                                msg.attach(txt)
                                txt = MIMEText(yaml.safe_dump(ami), 'yaml')
                                msg.attach(txt)
                                smtp = smtplib.SMTP('localhost')
                                smtp.sendmail(self.mailfrom, emails.split(','), msg.as_string())
                                smtp.quit()
                    except Exception, err:
                        self.logger.error('WatchmanProcess: saving result failed, %s', err)
                    self.logger.info('Transaction ' + transaction_id + ' finished. Result: ' + resfile)
                    self.resultdic.pop(transaction_id)
