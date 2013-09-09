Flask-CDN
=========

[![Build Status](https://travis-ci.org/wichitacode/flask-cdn.png)](https://travis-ci.org/wichitacode/flask-cdn)

Serve the static files in your Flask app from a CDN.

Documentation
-------------
The latest documentation for Flask-CDN can be found [here](https://flask-cdn.readthedocs.org/en/latest/).

Local-Projects
-------------
This has been intuitively integrated into the rackspace files API
Additionally a HEAD check is done on all remote files, and if it does not exist (or no permission)
we failsafe to a local request.