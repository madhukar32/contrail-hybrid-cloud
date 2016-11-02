#This module helps to manage all the functons related to the VPC creation and other
#More details will be uploaded once everything is working

from aws.connectAws import connectAws
from aws.util import (awsTag, awsResourceId)

from boto3.s3.transfer import ClientError

from hybridLogger import hybridLogger

from exception import *

class vpc(hybridLogger):
    
    def __init__(self, **kwargs):

        self.log = super(vpc, self).log(name=vpc.__name__)
        try:
            self.ec2Client = connectAws.getEc2Client()
            self.ec2 = connectAws.getEc2Resource()
        except ClientError as e:
            raise AwsError(boto3Api="getEc2Client", error=e)

    def createVpc(self, **kwargs):

        "Creates Vpc in AWS using boto3 python API"

        _requiredArgs = ['vpcName', 'cidrBlock']

        try:
            cidrBlock = kwargs['cidrBlock']
            self.vpcName = kwargs['vpcName']
        except KeyError:
            raise ArguementError(_requiredArgs, vpc.createVpc.__name__)


        #Create Vpc
        try:
            vpcResp = self.ec2Client.create_vpc(DryRun=False, CidrBlock= cidrBlock)
        except ClientError as e:
            if e.response['Error']['Code'] == 'AuthFailure':
                self.log.error("AWS authentication failed, please check your credentials in ~/.aws/credentails.\n Error details: {0}".format(e), exc_info=True)
                return False
            else:
                raise AwsError(boto3Api="create_vpc", error=e)

        vpcId = vpcResp.get('Vpc').get('VpcId')

        #Check if Vpc is available
        vpcWaiter = self.ec2Client.get_waiter('vpc_available')
        try:
            vpcWaiter.wait(VpcIds=[vpcId])
        except Exception as e:
            self.log.error("Vpc available waiter failed with error: {0}".format(e), exc_info=True)
            return False

        self.log.info("Vpc created with id {0}".format(vpcId))
        retValue = {'vpcId': vpcId}
        
        #Get Resource ID
        try:
            routeTableIdList = awsResourceId.getResourceIdWithVpc(self.ec2Client,
                            vpcResource='RouteTable', vpcId = vpcId)
            
            networkAclIdList = awsResourceId.getResourceIdWithVpc(self.ec2Client, 
                            vpcResource='NetworkAcl', vpcId = vpcId)
            
            securityGroupIdList = awsResourceId.getResourceIdWithVpc(self.ec2Client, 
                            vpcResource='SecurityGroup', vpcId = vpcId) 
        except (ArguementError, KeyError, AwsError) as e:
            self.log.error("Failed while fetching the ResourceId : {0}".format(e), exc_info=True)
            return False
        try:
            routeTableId = routeTableIdList[0]
            securityGroupId = securityGroupIdList[0]
            networkAclId = networkAclIdList[0]
        except KeyError as e:
            self.log.error(e, exc_info=True)
            return False


        if len(routeTableIdList) > 1:
            self.log.warn("Multiple routeTableId with the same Tag, condifering the first Id")

        if len(networkAclIdList) > 1:
            self.log.warn("Multiple networkAclId with the same Tag, condifering the first Id")

        if len(securityGroupIdList) > 1:
            self.log.warn("Multiple securityGroupId with the same Tag, condifering the first Id")
        
        #Assign tag to those resources
        #try:
        #    awsTag.assignTag(self.ec2, name='Name', value=self.vpcName, resourceIdList=[vpcId,
        #                 routeTableId, networkAclId, securityGroupId ])
        #except (ArguementError, AwsError) as e:
        #    self.log.error(e, exc_info=True)
        #    return False

        #Debug Log

        self.log.debug("RouteTable \t routeTableId: {}".format(routeTableId))
        self.log.debug("NetworkACL \t networkAclId: {}".format(networkAclId))
        self.log.debug("SecurityGroup \t securityGroupId: {}".format(securityGroupId))

        retValue['routeTableId'] = routeTableId 
        retValue['networkAclId'] = networkAclId 
        retValue['securityGroupId'] = securityGroupId

        return retValue

    def createSubnet(self, **kwargs):

        _requiredArgs = ['vpcId', 'vpcSubnet']
        try:
            vpcSubnet = kwargs['vpcSubnet']
            vpcId = kwargs['vpcId']
        except KeyError:
            raise ArguementError(_requiredArgs,vpc.createSubnet.__name__)

        try:
            vpc = self.ec2.Vpc(vpcId)
            subnetResp = vpc.create_subnet(CidrBlock=vpcSubnet)
        except Exception as e:
            raise AwsError(boto3Api="create_subnet", error=e)
        
        subnetId = subnetResp.id
        #self._assignTag(name='Name', value=self.vpcName, ResourceId=[self.subnetId])

        # try:
        #     awsTag.assignTag(self.ec2, name='Name', value=self.vpcName, resourceIdList=[subnetId])
        # except (ArguementError, AwsError) as e:
        #     self.log.error(e,exc_info=True)
        #     return False

        self.log.info("Subnet Created with Id: {0}".format(subnetId))
        retValue = {'subnetId': subnetId}
        return retValue

    def associateSubnetWithRouteTable(self, **kwargs):

        _requiredArgs = ['routeTableId', 'subnetId']
        try:
            routeTableId = kwargs['routeTableId']
            subnetId = kwargs['subnetId']
        except KeyError:
            raise ArguementError(_requiredArgs,vpc.createSubnet.__name__)

        try:
            routeTable = self.ec2.RouteTable(routeTableId)
            routeTableAssociation = routeTable.associate_with_subnet(SubnetId = subnetId)
        except Exception as e:
            raise AwsError(boto3Api="associate_with_subnet", error=e)

        self.log.info("Associated Route Table {0} with the subnet {1}".format(routeTableId, subnetId))
        self.log.debug("routeTable response: {0}".format(routeTable))
        self.log.debug("routeTableAssociatio response: {0}".format(routeTableAssociation))
        return True

