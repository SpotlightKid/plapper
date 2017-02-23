# -*- coding: utf-8 -*-
#
# app.py
#
"""A Bottle web service for blog comments."""

from __future__ import print_function, unicode_literals

import argparse
import logging
import sys

from wsgiref.simple_server import make_server, WSGIRequestHandler

import bottle

log = logging.getLogger(__file__)
app = bottle.Bottle()


@app.get('/')
def hello():
    return {'msg': "Hello world!"}


class QuietServer(bottle.WSGIRefServer):
    def run(self, handler):
        if self.quiet:
            base = self.options.get('handler_class', WSGIRequestHandler)

            class QuietHandler(base):
                def log_request(*args, **kw):
                    pass

            self.options['handler_class'] = QuietHandler

        self.srv = make_server(self.host, self.port, handler, **self.options)
        self.port = self.srv.server_port
        self.srv.serve_forever(poll_interval=0.1)


def main(args=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('-v', '--verbose', action="store_true",
        help="Be verbose")

    args = ap.parse_args(args if args is not None else sys.argv[1:])

    logging.basicConfig(format="%(name)s: %(levelname)s - %(message)s",
        level=logging.DEBUG if args.verbose else logging.INFO)

    try:
        server = QuietServer(host='0.0.0.0', port=8080)
        app.run(server=server, debug=True, quiet=True)
    except KeyboardInterrupt:
        pass
    finally:
        server.srv.server_close()
        print("Server shut down.")


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]) or 0)
