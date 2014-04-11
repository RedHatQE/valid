import multiprocessing
import BaseHTTPServer
import urlparse
import ssl
import logging
import yaml
import traceback

import valid


class ServerProcess(multiprocessing.Process):
    """
    Process for handling HTTPS requests
    """
    def __init__(self, shareddata):
        """
        Create ServerProcess object

        @param hostname: bind address
        @type hostname: str

        @param port: bind port
        @type port: int
        """
        self.hostname = shareddata.hname
        self.port = shareddata.port
        multiprocessing.Process.__init__(self, name='ServerProcess', target=self.runner, args=(shareddata,))

    def runner(self, shareddata):
        """
        Run process
        """
        server_class = ValidHTTPServer
        httpd = server_class((self.hostname, self.port), ValidHTTPHandler, shareddata)
        httpd.socket = ssl.wrap_socket(httpd.socket,
                                       certfile=shareddata.yamlconfig['server_ssl_cert'],
                                       keyfile=shareddata.yamlconfig['server_ssl_key'],
                                       server_side=True,
                                       cert_reqs=ssl.CERT_REQUIRED,
                                       ca_certs=shareddata.yamlconfig['server_ssl_ca'])
        httpd.serve_forever()


class ValidHTTPServer(BaseHTTPServer.HTTPServer):
    """ Valid HTTPS server """

    def __init__(self, server_address, RequestHandlerClass, shareddata):
        BaseHTTPServer.HTTPServer.__init__(self, server_address, RequestHandlerClass)
        self.shareddata = shareddata


class ValidHTTPHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    """
    HTTP Handler
    """
    def __init__(self, request, client_address, server):
        BaseHTTPServer.BaseHTTPRequestHandler.__init__(self, request, client_address, server)

    def do_HEAD(self):
        """
        Process HEAD request
        """
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        """
        Process GET request
        """
        logger = logging.getLogger('valid.runner')
        try:
            path = urlparse.urlparse(self.path).path
            query = urlparse.parse_qs(urlparse.urlparse(self.path).query)
            logger.debug('GET request: ' + self.path)
            if path[-1:] == '/':
                path = path[:-1]
            if path == '':
                # info page
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write('<html><head><title>Validation status page</title></head>')
                self.wfile.write('<body>')
                self.wfile.write('<h1>Worker\'s queue</h1>')
                for q_item in self.server.shareddata.mainq.queue:
                    self.wfile.write('<p>%s</p>' % str(q_item))
                self.wfile.write('<h1>Ongoing testing</h1>')
                for transaction_id in self.server.shareddata.resultdic.keys():
                    self.wfile.write('<h2>Transaction <a href=/result?transaction_id=%s>%s</a></h2>' % (transaction_id, transaction_id))
                    for ami in self.server.shareddata.resultdic[transaction_id].keys():
                        self.wfile.write('<h3>Ami %s </h3>' % ami)
                        self.wfile.write('<p>%s</p>' % str(self.server.shareddata.resultdic[transaction_id][ami]))
                self.wfile.write('<h1>Finished testing</h1>')
                for transaction_id in self.server.shareddata.resultdic_yaml.keys():
                    self.wfile.write('<h2>Transaction <a href=/result?transaction_id=%s>%s</a></h2>' % (transaction_id, transaction_id))
                self.wfile.write('</body></html>')
            elif path == '/result':
                # transaction result in yaml
                if not 'transaction_id' in query.keys():
                    raise Exception('transaction_id parameter is not set')
                transaction_id = query['transaction_id'][0]
                if transaction_id in self.server.shareddata.resultdic_yaml.keys():
                    self.send_response(200)
                    self.send_header('Content-type', 'text/yaml')
                    self.end_headers()
                    self.wfile.write(self.server.shareddata.resultdic_yaml[transaction_id])
                else:
                    if transaction_id in self.server.shareddata.resultdic.keys():
                        self.send_response(200)
                        self.send_header('Content-type', 'text/yaml')
                        self.end_headers()
                        self.wfile.write(yaml.safe_dump({'result': 'In progress'}))
                    else:
                        raise Exception('No such transaction')
            else:
                self.send_response(404)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write('<html><body>Bad url</body></html>')
        except Exception, err:
            self.send_response(400)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(err.message)
            logger.debug('HTTP Server:' + traceback.format_exc())

    def do_POST(self):
        """
        Process POST request
        """
        logger = logging.getLogger('valid.runner')
        # Extract and print the contents of the POST
        length = int(self.headers['Content-Length'])
        try:
            post_data = urlparse.parse_qs(self.rfile.read(length).decode('utf-8'))
            if post_data and ('data' in post_data.keys()):
                data = yaml.load(post_data['data'][0])
                logger.debug('POST DATA:' + str(data))
                if 'emails' in post_data.keys():
                    emails = post_data['emails'][0]
                    logger.debug('POST EMAILS:' + emails)
                else:
                    emails = None
                if 'subject' in post_data.keys() and emails:
                    subject = post_data['subject'][0]
                    logger.debug('POST SUBJECT:' + subject)
                else:
                    subject = None
                transaction_id = valid.valid_misc.add_data(self.server.shareddata, data, emails, subject)
                if not transaction_id:
                    raise Exception('Bad data')
                self.send_response(200)
                self.send_header('Content-type', 'text/yaml')
                self.end_headers()
                self.wfile.write(yaml.safe_dump({'transaction_id': transaction_id}))
            else:
                raise Exception('Bad data')
        except Exception, err:
            self.send_response(400)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(err.message)

