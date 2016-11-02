from exception import *
from vnc_api import vnc_api

class vncObj():

    @staticmethod
    def get(**kwargs):

        _requiredArgs = ['username', 'tenantName', 'password', 'apiHost' ]
        try:
            userName = kwargs['username']
            tenantName = kwargs['tenantName']
            password = kwargs['password']
            apiHost = kwargs['apiHost']
        except KeyError:
            raise ArguementError(_requiredArgs, vncNetwork.__name__)

        try:
            authHost = kwargs['auth_host']
        except KeyError:
            authHost = apiHost

        try:
            return vnc_api.VncApi(username=userName, password=password, tenant_name=tenantName,
                    api_server_host = apiHost, auth_host = authHost)
        except Exception as e:
            raise ContrailError(vncApi='vnc_api.VncApi', error=e)

def readTenant(vncObj, domain=None, tenantName=None):

    if not domain or not tenantName:
        raise ArguementError('domain, tenantName', readTenant.__name__)

    try:
        return vncObj.project_read(fq_name = [domain, tenantName])
    except Exception as e:
        raise ContrailError(vncApi='vncObj.project_read', error=e)

def readNetwork(vncObj, domain=None, tenantName=None, networkName=None):

    if not domain or not tenantName or not networkName:
        raise ArguementError('domain, tenantName', networkName, readNetwork.__name__)

    try:
        return vncObj.virtual_network_read(fq_name = [domain, tenantName, networkName])
    except Exception as e:
        raise ContrailError(vncApi='vncObj.virtual_network_read', error=e)

def readPolicy(vncObj, domain=None, tenantName=None, policyName=None):

    if not domain or not tenantName or not policyName:
        raise ArguementError('domain, tenantName', networkName, readPolicy.__name__)

    try:
        return vncObj.network_policy_read(fq_name = [domain, tenantName, policyName])
    except Exception as e:
        raise ContrailError(vncApi='vncObj.network_policy_read', error=e)

def readSvcTemplate(vncObj, fqName):
    
    try:
        return vncObj.service_template_read(fq_name = fqName)
    except Exception as e:
        raise ContrailError(vncApi='vncObj.service_template_read', error=e)
