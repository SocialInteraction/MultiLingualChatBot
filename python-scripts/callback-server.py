from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from urllib.parse import urlparse, parse_qs
import logging

class CustomRequestHandler(BaseHTTPRequestHandler):
    server_data = None

    def _set_response(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

    def do_GET(self):
        logging.info("GET request,\nPath: %s\nHeaders:\n%s\n", str(self.path), str(self.headers))
        parsed_url = urlparse(self.path)
        sender = parse_qs(parsed_url.query)['sender'][0]
        print("Current server data is ", CustomRequestHandler.server_data)
        self._set_response()
        
        if CustomRequestHandler.server_data is not None:
            if CustomRequestHandler.server_data.get(sender) is not None:
                self.wfile.write(CustomRequestHandler.server_data[sender].encode('utf-8'))
            else:
                self.wfile.write("".encode('utf-8'))
        else:
            self.wfile.write("".encode('utf-8'))

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])                                      #get size of the data
        post_data = self.rfile.read(content_length)                                               #get the data
        logging.info("POST request,\nPath: %s\nHeaders:\n%s\n\nBody:\n%s\n",
                str(self.path), str(self.headers), post_data.decode('utf-8'))
        temp = json.loads(post_data.decode('utf-8'))
        
        if CustomRequestHandler.server_data is not None:
            CustomRequestHandler.server_data[temp["recipient_id"]] = json.dumps(temp)
        else:
            CustomRequestHandler.server_data = {}
            CustomRequestHandler.server_data[temp["recipient_id"]] = json.dumps(temp)
        
        print("Current server data is ", CustomRequestHandler.server_data)
        self._set_response()

def run(server_class=HTTPServer, handler_class=CustomRequestHandler, port=8080):
    logging.basicConfig(level=logging.INFO)
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    logging.info('Starting http server at port %d\n', port)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    print("\n")
    logging.info('Stopping http server\n')

if __name__ == '__main__':
    from sys import argv

    if len(argv) == 2:
        run(port=int(argv[1]))
    else:
        run()