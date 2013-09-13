# -*- coding: utf-8 -*-
"""
    :copyright: (c) 2013 Local Projects, all rights reserved
    :license: Affero GNU GPL v3, see LICENSE for more details.
"""

import random
import shutil
import yaml
import pyrax
import string
import os
from PIL import Image

from collections import namedtuple
from flask import g, current_app
from werkzeug import secure_filename, FileStorage


# simple return type
UploadedImage = namedtuple('UploadedImage', 'success path name url')

def upload_rackspace_image(resource, resource_name = None):
    if hasattr(current_app, 'cdn_rackspace'):
        return current_app.cdn_rackspace.upload_rackspace_image(resource, resource_name)

    # not properly initialized
    warnStr = "Called upload_rackspace_image without a proper initialization of the plugin"
    current_app.logger.warn(warnStr)

    return UploadedImage(False, '', '', '')


class CDN_RACKSPACE(object):

    def __init__(self, app):
        self.rackspace_endpoint = 'rackspace'
        self.app = app
        self.container = self.get_rackspace_container()
        self.rackspace_url = self.get_rackspace_url()
        # adding the 'rackspace' endpoint
        self.app.add_url_rule('/<path:filename>',
                              endpoint=self.rackspace_endpoint)
        
        print "We've initialized the rackspace"

    def _string_generator(self, size=6, chars=string.ascii_lowercase + string.digits):
        return ''.join(random.choice(chars) for x in range(size))

    def _lowercase_ext(self, filename):
        if '.' in filename:
            main, ext = filename.rsplit('.', 1)
            return main + '.' + ext.lower()
        else:
            return filename.lower()


    def get_rackspace_container(self):

        # TODO ensure we can have concurrent pyraxes for multiple apps
        pyrax.set_setting( "identity_type", "rackspace" )
        pyrax.set_credentials( self.app.config['CDN_RACKSPACE_USERNAME'], self.app.config['CDN_RACKSPACE_KEY'] )

        cf = pyrax.connect_to_cloudfiles( self.app.config['CDN_RACKSPACE_REGION'] )
        container = cf.create_container( self.app.config['CDN_RACKSPACE_CONTAINER'] )

        container.make_public()

        return container


    def get_rackspace_url(self):
        return self.container.cdn_uri


    def does_rackspace_file_exist(self, file_name):

        try:
            file_object = self.container.get_object( file_name )
            return True

        except pyrax.exceptions.NoSuchObject as e:
            return False


    def upload_rackspace_image(self, resource, resource_name = None):

        """
        unfortunately the following needs to happen

        - test that it's an allowed extension
        - test to see if the file name is OK locally
        - test to see if the file name is OK remotely
        - generate file names
        """

        base_path = self.app.config['CDN_HOSTED_IMAGES_LOCAL_DIR']
        allowed_extensions = self.app.config['CDN_ALLOWED_EXTENSIONS']

        if not (    isinstance(resource, FileStorage) 
                 or isinstance(resource, str)
                 or isinstance(resource, Image.Image) ):

            raise TypeError("resouece must be a werkzeug.FileStorage or string or Image.  resource is {0}".format(type(resource)))


        if isinstance( resource, str ):
            filename = resource
        elif isinstance( resource, FileStorage ):
            filename = resource.filename
        elif isinstance( resource, Image.Image ):
            filename = resource_name
        else:
            raise TypeError("resouece must be a werkzeug.FileStorage or string or Image")


        file_path, basename = os.path.split(filename) 

        fullname = self._lowercase_ext(secure_filename( basename ))
        
        # split it into parts
        file_base_name, file_extension = os.path.splitext(fullname)

        # they wanted a bad extension
        if file_extension not in allowed_extensions:
            if g.is_anonymous:
                infoStr = "Anonymous user tried to upload bad file extension {0}".format( local_file )
            else:
                infoStr = "User {0} tried to upload bad file extension {1}".format( g.user.id, local_file )
            self.app.logger.infoStr( infoStr )
            return UploadedImage( False, '', '' )


        # if we got this far let's make sure the name is not taken
        sanity_check = 0
        max_sanity_check = 20

        new_file = filename
        full_file_path = os.path.join( base_path, new_file )

        while (   

            ( os.path.isfile(full_file_path) 
              or self.does_rackspace_file_exist(new_file) )

            and sanity_check < max_sanity_check  
        ):

            # check it doesn't exist locally
            # check it doesn't exist in the cloud

            new_file = "{0}.{1}.{2}{3}".format( file_base_name,
                                                sanity_check,
                                                self._string_generator(2),
                                                file_extension )

            full_file_path = os.path.join( base_path, new_file )

            sanity_check += 1

        if sanity_check >= max_sanity_check:
            user = "anonymous" if g.user.is_anonymous() else g.user.id
            errStr = "We reached a sanity check while trying to upload file {0} for user {1}".format(local_file, 
                                                                                                     user)
            self.app.logger.error(errStr)

            return UploadedImage( False, '', '', '' )

        # otherwise let's make both a local copy and a remote copy
        try:
            if isinstance( resource, str ):
                shutil.copy( resource, full_file_path )
            elif isinstance( resource, FileStorage ):
                resource.save( full_file_path )
            elif isinstance( resource, Image.Image ):
                resource.save( full_file_path )
            else:
                raise TypeError("resouece must be a werkzeug.FileStorage or string or Image.  resource is {0}".format(type(resource)))

        except Exception as e:
            errStr = "Error trying to save local file to {0}".format( full_file_path )
            self.app.logger.error(errStr)
            self.app.logger.exception(e)
            return UploadedImage( False, '', '', '' )

        try:

            # use the renaimed file
            self.container.upload_file( full_file_path )

        except Exception as e:
            errStr = "Error trying to upload file to rackspace system."
            self.app.logger.error(errStr)
            self.app.logger.exception(e)

            return UploadedImage( False, '', '', '' )


        url = self.rackspace_url + '/' + new_file
        return UploadedImage( True, full_file_path, new_file, url )

