class ArguementError(Exception):

    def __init__(self, arguements, name):

        self.missingVariables = arguements
        self.functionName = name

    def __str__(self):
        return 'Function {0} required arguements: {1}'.format(self.functionName, self.missingVariables)

class AwsError(Exception):

    def __init__(self, boto3Api=None, error=None):

        self.error = error
        self.boto3Api = boto3Api 

    def __str__(self):

        return 'While calling boto3 API: {0} Details: {1}'.format(self.boto3Api,self.error)

class ContrailError(Exception):

    def __init__(self, vncApi=None, error=None):

        self.error = error
        self.vncApi = vncApi

    def __str__(self):

        return 'While calling vncApi: {0} Details: {1}'.format(self.vncApi,self.error)
