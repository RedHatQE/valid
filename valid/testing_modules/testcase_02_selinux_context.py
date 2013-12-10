import re
import yaml
import os
import tempfile
import paramiko
from valid.valid_testcase import *


class testcase_02_selinux_context(ValidTestcase):
    """
    Check if the kickstart restores selinux appropriately
    """
    stages = ['stage1']
    tags = ['default']

    def test(self, connection, params):
        prod = params['product'].upper()
        ver = params['version']
        #get the restorecon output file
        self.ping_pong(connection, "restorecon -R -v -n -e /proc -e /sys / | sed -e 's, context , ,' -e 's,^restorecon reset ,,' | cat > /tmp/restorecon_output.txt && echo SUCCESS", "\r\nSUCCESS\r\n", 260)
        tf = tempfile.NamedTemporaryFile(delete=False)
        tf.close()
        connection.sftp.get('/tmp/restorecon_output.txt', tf.name)
        output = open(tf.name, 'r')
        result = output.read()
        output.close()
        os.unlink(tf.name)
        # convert output file into a dictionary to be able to compare with allowed selinux exclusions
        result = result.split("\n")
        result.pop()
        restorecon_dict = {}
        for line in result:
            filename = line.split(" ")[0]
            context = line.split(" ")[1]
            source_context = context.split(":")[2]
            destination_context = context.split(":")[5]
            restorecon_dict[filename] = [source_context, destination_context]
        #figure out if there are new/lost entries or the restorecon output matched the list of allowed exclusions
        with open('/usr/share/valid/data/selinux_context.yaml') as selinux_context:
            context_exclusions_ = yaml.load(selinux_context)
        try:
            context_exclusions = context_exclusions_['%s_%s' % (prod, ver)]
        except KeyError as e:
            self.log.append({
                'result': 'skip',
                'comment': 'unsupported product-version combination'})
            return self.log

        lost_entries = []
        for filename in context_exclusions:
            pattern = re.compile('%s' % filename)
            matched = False
            for filename_rest in restorecon_dict:
                    match_result = pattern.match(filename_rest)
                    if match_result and context_exclusions[filename] == restorecon_dict[filename_rest]:
                        matched = True
                        break
            if not matched:
                lost_entries.append([filename, context_exclusions[filename]])

        new_entries = []
        for filename_rest in restorecon_dict:
            matched = False
            for filename in context_exclusions:
                pattern = re.compile('%s' % filename)
                match_result = pattern.match(filename_rest)
                if match_result and context_exclusions[filename] == restorecon_dict[filename_rest]:
                    matched = True
                    break
            if not matched:
                new_entries.append([filename_rest, restorecon_dict[filename_rest]])

        if new_entries == [] and lost_entries != []:
            self.log.append({'result': 'warning', 'comment': '\nLost entries:' + str(lost_entries)})
        if new_entries == lost_entries == []:
            self.log.append({'result': 'passed', 'comment': 'No new or lost entries detected. Restorecon output file matches with the list of allowed SElinux context discrepancies.'})
        if new_entries != []:
            self.log.append({'result': 'failed', 'comment': '\nFail.New entries detected:' + str(new_entries) + '\nLost entries:' + str(lost_entries)})
        return self.log
