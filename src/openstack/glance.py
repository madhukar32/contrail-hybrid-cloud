from credentials import get_nova_credentials, get_keystone_credentials
import os

import keystoneclient.v2_0.client as ksclient
import glanceclient

from hybridLogger import hybridLogger

class glance(hybridLogger):

    def __init__(self, **kwargs):

        logLevel = kwargs.get('logLevel', 'INFO')
        self.log = super(glance, self).log(level=logLevel, name=glance.__name__)
        try:
            creds = get_keystone_credentials()
            keystone = ksclient.Client(**creds)
            glance_endpoint = keystone.service_catalog.url_for(service_type='image',
                                    endpoint_type='publicURL')
            self.glance = glanceclient.Client('1',glance_endpoint, 
                            token=keystone.auth_token)
        except Exception as e:
            raise Exception(e.message)


    def createImage(self, **kwargs):

        filePath = kwargs['filePath']
        imageName = kwargs['imageName']

        public = kwargs.get('public', False)
        diskFormat = kwargs.get('diskFormat', 'qcow2')
        containerFormat = kwargs.get('containerFormat', 'bare')

        with open(filePath) as fimage:
            self.glance.images.create(name=imageName, is_public=True, disk_format=diskFormat,
                        container_format=containerFormat,data=fimage)
        fimage.close()

    def verifyImage(self, imageName):

        imageGen = self.glance.images.list()

        for image in list(imageGen):
            if imageName == image.name:
                return True

        return False
