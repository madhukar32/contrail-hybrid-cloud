from boto3.s3.transfer import ClientError
from exception import *

class awsTag(object):
    
    @staticmethod
    def assignTag(ec2, **kwargs):
        
        _requiredArgs = ['name', 'value', 'resourceIdiList']
        try:
            name = kwargs['name']
            value = kwargs['value']
            resourceIdList = kwargs['resourceIdList']
        except KeyError:
            raise ArguementError(_requiredArgs, awsTag.assignTag.__name__)

        tags=[{'Key': name, 'Value': value}]

        try:
            ec2.create_tags(Resources=resourceIdList, Tags=tags)
        except ClientError as e:
            raise AwsError(boto3Api="create_tags", error=e)

class awsResourceId(object):

    @staticmethod
    def getResourceIdWithVpc(ec2Client, **kwargs):

        _requiredArgs = ['vpcResource', 'vpcId']

        validDescribeFunction = {
                'RouteTable': ec2Client.describe_route_tables,
                'NetworkAcl': ec2Client.describe_network_acls,
                'SecurityGroup': ec2Client.describe_security_groups,
                'Subnet': ec2Client.describe_subnets
        }

        validTags = {
                'SecurityGroup': {'KeyName': 'SecurityGroups', 'Id': 'GroupId'},
                'NetworkAcl'   : {'KeyName': 'NetworkAcls',    'Id': 'NetworkAclId'},
                'RouteTable'   : {'KeyName': 'RouteTables',    'Id': 'RouteTableId'},
                'Subnet'       : {'KeyName': 'Subnets',        'Id': 'SubnetId'}
        }

        try:
            resource = kwargs['vpcResource']
            vpcId = kwargs['vpcId']
        except KeyError:
            raise ArguementError(_requiredArgs, awsResourceId.getResourceIdWithVpc.__name__)

        try:
            describeFunction = validDescribeFunction[resource]
        except KeyError as e:
            raise KeyError("Cannot fetch a describe function for the resource {0} \nAvailable describe functions are: {1} \nError: {2}".format(resource, validDescribeFunction, error, e))

        resourceFilter = [{'Name': 'vpc-id', 'Values': [vpcId]}]

        try:
            describeResp = describeFunction(Filters=resourceFilter)
        except ClientError as e:
            raise AwsError(boto3Api=describeFunction, error=e)

        resourceDetails = validTags[resource]
        resourceIdList = []
        
        for eachResource in describeResp[resourceDetails['KeyName']]:
            resourceIdList.append(eachResource[resourceDetails['Id']])

        return resourceIdList
