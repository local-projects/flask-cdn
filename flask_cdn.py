import os

from urlparse import urlparse
import requests

from flask import url_for as flask_url_for
from flask import current_app

from flask_cdn_rackspace import CDN_RACKSPACE

def url_for(endpoint, **values):
    """
    Generates a URL to the given endpoint.

    If the endpoint is for a static resource then a URL to the CDN is
    generated, otherwise the call is passed on to `flask.url_for`.

    Because this function is set as a jinja environment variable when
    `CDN.init_app` is invoked, this function replaces `flask.url_for` in
    templates automatically. It is unlikely that this function will need to be
    directly called from within your application code, unless you need to refer
    to static assets outside of your templates.

    Actually we do this now because it allows us to switch between local static
    and flask assets
    """
    app = current_app

    if app.debug and not app.config['CDN_DEBUG']:

        return flask_url_for(endpoint, **values)

    if endpoint == 'static':
        scheme = 'http'
        if app.config['CDN_HTTPS']:
            scheme = 'https'

        # rackspace does not include the /static, everything is container.com/item.jpg
        if  app.config['CDN_USE_RACKSPACE']:
            rack_url = app.cdn_rackspace.rackspace_url
            rack_parts = urlparse(rack_url)
            rack_bare_url = rack_parts.netloc + rack_parts.path

            """
              note originally we tried to use the flask native url_for, but it kept adding the
              endpoint to the url, such as "gfgfgf.rackspace.com/rackspace/file.htm"

              in flask_cdn_rackspace.py : init
                self.rackspace_endpoint = 'rackspace'

                # adding the 'rackspace' endpoint
                self.app.add_url_rule('/' + self.rackspace_endpoint + '/<path:filename>',
                                     endpoint=self.rackspace_endpoint)

              in this file:
                urls = app.url_map.bind( rack_bare_url, url_scheme=scheme )
                # swap out with the rackspace endpoint rule to avoid the '/static/' path
                url = urls.build(endpoint = app.cdn_rackspace.rackspace_endpoint, values=values, force_external=True)
            """

            url = rack_parts.scheme + "://" + rack_parts.netloc + "/" + values['filename']

            if app.config['CDN_RACKSPACE_HEAD_TEST']:
                # test the url
                resp = requests.head(url)
                if resp.status_code == 200:
                    # use remote url
                    return url
                else:
                    # fall back to the local static dir
                    
                    return flask_url_for(endpoint, **values)
            else:
                # just return the url
                return url


        urls = app.url_map.bind(app.config['CDN_DOMAIN'], url_scheme=scheme)

        if app.config['CDN_TIMESTAMP']:
            path = os.path.join(app.static_folder, values['filename'])
            values['t'] = int(os.path.getmtime(path))

        return urls.build(endpoint, values=values, force_external=True)

    return flask_url_for(endpoint, **values)



class CDN(object):
    """
    The CDN object allows your application to use Flask-CDN.

    When initialising a CDN object you may optionally provide your
    :class:`flask.Flask` application object if it is ready. Otherwise,
    you may provide it later by using the :meth:`init_app` method.

    :param app: optional :class:`flask.Flask` application object
    :type app: :class:`flask.Flask` or None
    """
    def __init__(self, app=None):
        """
        An alternative way to pass your :class:`flask.Flask` application
        object to Flask-CDN. :meth:`init_app` also takes care of some
        default `settings`_.

        :param app: the :class:`flask.Flask` application object.
        """
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        defaults = [('CDN_DOMAIN', None),
                    ('CDN_DEBUG', False),
                    ('CDN_HTTPS', False),
                    ('CDN_TIMESTAMP', True),
                    ('CDN_USE_RACKSPACE', False),
                    ('CDN_RACKSPACE_HEAD_TEST', False)]

        for k, v in defaults:
            app.config.setdefault(k, v)

        if app.config['CDN_DOMAIN']:
            app.jinja_env.globals['url_for'] = url_for

        if app.config['CDN_USE_RACKSPACE']:
            app.cdn_rackspace = CDN_RACKSPACE(app)

            if app.config['CDN_HTTPS']:
                warnStr = "Warning, rackspace file hosting and CDN_HTTPS shouldn't be used together due to cert domain issues."
                app.logger.warning(warnStr)

