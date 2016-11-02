import boto3

class connectAws():

    @staticmethod
    def getEc2Client():

        return boto3.client('ec2')

    @staticmethod
    def getEc2Resource():

        return boto3.resource('ec2')

