from aws.vpc import vpc
from aws.util import (awsTag, awsResourceId)
from exception import *

import pdb
import sys
import time

class vpnConnection(vpc):
    
    def __init__(self, **kwargs):
        super(vpnConnection, self).__init__()
        

    def createCustomerGw(self, **kwargs):

        _requiredArgs = ['gatewayIP', 'customerCidrBlock', 'sgId']
        try:
            gatewayIp = kwargs['gatewayIP']
            customerCidrBlock = kwargs['customerCidrBlock']
            sgId = kwargs['sgId']
        except KeyError as e:
            raise ArguementError(_requiredArgs, vpnConnection.createCustomerGw.__name__)

        bgpAsn = kwargs.get('bgpAsn', 65000)

        try:
            custGw = self.ec2Client.create_customer_gateway(Type='ipsec.1', PublicIp=gatewayIp,BgpAsn=bgpAsn)
            custGwId = custGw['CustomerGateway']['CustomerGatewayId']
        except Exception as e:
            raise AwsError(boto3Api="create_customer_gateway", error=e)

        self.log.info("Customer Gateway is created with Id: {0}".format(custGwId))

        try:
            self.updateSg(custCidrIp=customerCidrBlock, sgId = sgId)
        except AwsError as e:
            self.log.error(e, exc_info=True)

        retValue = {'customerGatewayId': custGwId}
        return retValue

    
    def createVpnGw(self, **kwargs):

        _requiredArgs = ['vpcId', 'routeTableId']
        try:
            vpcId = kwargs['vpcId']
            routeTableId = kwargs['routeTableId']
        except KeyError as e:
            raise ArguementError(_requiredArgs, vpnConnection.createVpnGw.__name__)

        try:
            vpnGw = self.ec2Client.create_vpn_gateway(Type='ipsec.1')
            time.sleep(1)
            vpnGwId = vpnGw['VpnGateway']['VpnGatewayId'] 
        except Exception as e:
            raise AwsError(boto3Api="create_vpn_gateway", error=e)
        
        self.log.info("Virtual Private Gateway is created with Id: {0}".format(vpnGwId))

        try:
            attachResp = self.ec2Client.attach_vpn_gateway(VpnGatewayId=vpnGwId, VpcId=vpcId)
            time.sleep(10)
        except Exception as e:
            raise AwsError(boto3Api="attach_vpn_gateway", error=e)
        
        self.log.info("Attached vpn gateway to vpc: {0}".format(vpcId))

        try:
            enableResp = self.ec2Client.enable_vgw_route_propagation(RouteTableId=routeTableId, 
                                        GatewayId=vpnGwId)
        except Exception as e:
            raise AwsError(boto3Api="enable_vgw_route_propagation", error=e)
        
        
        self.log.info("Enabled virtual gateway route propogation")

        retValue = {'vpnGatewayId': vpnGwId}

        return retValue


    def updateSg(self, **kwargs):

        _requiredArgs = ['sgId', 'custCidrIp']
        try:
            sgId = kwargs['sgId']
            customerCidrBlock = kwargs['custCidrIp']
        except KeyError as e:
            raise ArguementError(_requiredArgs, vpnConnection.updateSg.__name__)

        
        securityGroup = self.ec2.SecurityGroup(sgId)
        try:
            ingressResp = securityGroup.authorize_ingress(IpPermissions=
                    [{'IpProtocol':'-1', 'IpRanges': [{'CidrIp': customerCidrBlock}]}])
            egressResp = securityGroup.authorize_egress(IpPermissions=
                    [{'IpProtocol':'-1', 'IpRanges': [{'CidrIp': customerCidrBlock}]}])
        except Exception as e:
            raise AwsError(boto3Api="authorize_ingress_egress", error=e)

        self.log.info("Updates ingress and egress security group of {0}".format(sgId))

        return True

    def createVpnConnection(self, **kwargs):

        _requiredArgs = ['custGwId', 'vpnGwId']
        try:
            custGwId = kwargs['custGwId']
            vpnGwId = kwargs['vpnGwId']
        except KeyError as e:
            raise ArguementError(_requiredArgs, vpnConnection.createVpnConnection.__name__)

        try:
            vpnCreationresp = self.ec2Client.create_vpn_connection(Type='ipsec.1', CustomerGatewayId=custGwId,
                    VpnGatewayId=vpnGwId, Options={'StaticRoutesOnly': True})
        except Exception as e:
            raise AwsError(boto3Api="create_vpn_connection", error=e)

        vpnConnectionId = vpnCreationresp['VpnConnection']['VpnConnectionId']

        self.log.info("VPN connection created with Id: {0}".format(vpnConnectionId))


        retValue = {'vpnConnectionId': vpnConnectionId}
        return retValue


    def createVpnRoute(self, **kwargs):

        _requiredArgs = ['customerCidrBlock', 'vpnConnectionId']
        try:
            customerCidrBlock = kwargs['customerCidrBlock']
            vpnConnectionId = kwargs['vpnConnectionId']
        except KeyError as e:
            raise ArguementError(_requiredArgs, vpnConnection.createVpnRoute.__name__)


        try:
            vpnCreationResp = self.ec2Client.create_vpn_connection_route(VpnConnectionId=vpnConnectionId,
                                    DestinationCidrBlock=customerCidrBlock)

        except Exception as e:
            raise AwsError(boto3Api="create_vpn_connection_route", error=e)

        self.log.info("Created vpn connection route")

        return True


    def getCustomerConfigInfo(self, **kwargs):

        _requiredArgs = ['vpnConnectionId']
        try:
            vpnConnectionId = kwargs['vpnConnectionId']
        except KeyError as e:
            raise ArguementError(_requiredArgs, vpnConnection.getCustomerConfigInfo.__name__)

        try:
            vpnDescribeResp = self.ec2Client.describe_vpn_connections(VpnConnectionIds=[vpnConnectionId])
        except Exception as e:
            raise AwsError(boto3Api="describe_vpn_connections", error=e)

        try:
            return vpnDescribeResp['VpnConnections'][0]['CustomerGatewayConfiguration']
        except KeyError:
            self.log.error("Something is wrong with the describe response", exc_info=True)
            return False

