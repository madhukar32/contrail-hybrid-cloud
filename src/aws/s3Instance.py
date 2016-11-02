from aws.connectAws import connectAws
from aws.util import (awsTag, awsResourceId)

from boto3.s3.transfer import ClientError

from hybridLogger import hybridLogger
from exception import *

import time

class s3Instance(hybridLogger):

    def __init__(self, **kwargs):

        self.log = super(s3Instance, self).log(name=s3Instance.__name__)
        try:
            self.ec2Client = connectAws.getEc2Client()
            self.ec2 = connectAws.getEc2Resource()
        except ClientError as e:
            raise AwsError(boto3Api="getEc2Client", error=e)


    def create(self, **kwargs):

        _requiredArgs = ['name', 'keyPairName', 'sgId', 'subnetId']

        try:
            keyPairName = kwargs['keyPairName']
            sgId = kwargs['sgId']
            subnetId = kwargs['subnetId']
            name = kwargs['name']
        except KeyError:
            raise ArguementError(_requiredArgs, s3Instance.create.__name__)

        imageId = kwargs.get('imageId', 'ami-b04e92d0')

        instanceType = kwargs.get('instanceType', 't2.micro')

        try:
            subnet = self.ec2.Subnet(subnetId)
            instances = subnet.create_instances(ImageId=imageId, MinCount=1, MaxCount=1,KeyName = keyPairName, 
                        SecurityGroupIds=[sgId], InstanceInitiatedShutdownBehavior='terminate',  
                        InstanceType=instanceType)
        except Exception as e:
            AwsError(boto3Api="subnet.create_instances", error=e)

        instanceIdList = [instance.id for instance in instances]

        try:
            awsTag.assignTag(self.ec2, name='Name', value=name, resourceIdList=instanceIdList)
        except (ArguementError, AwsError) as e:
            vpch.log.error(e, exc_info=True)
        
        instanceWaiter = self.ec2Client.get_waiter('instance_running')

        try:
            instanceWaiter.wait(InstanceIds=instanceIdList)
        except Exception as e:
            AwsError(boto3Api="waiter.instance_running", error=e)

        self.log.info("Instances created are: {0}".format(instanceIdList))

        retValue = {'instanceId': instanceIdList}

        return retValue
    
    @staticmethod
    def terminate(instanceId):

        instance = self.ec2.Instance(instanceId)

        try:
            return instance.terminate()
        except Exception as e:
            AwsError(boto3Api="instance.terminate", error=e)


