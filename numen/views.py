import boto3
import random
import time
import string
import re
from botocore.config import Config
from botocore.exceptions import ClientError
from django.shortcuts import render,redirect
from django.http import JsonResponse
import json
import logging
import datetime
import requests
import logging
import codecs
from django.middleware import csrf
from django.views.decorators.csrf import csrf_exempt
from jinja2 import Template
import subprocess
import uuid
import os


logger = logging.getLogger(__name__)

def health_check(request):
    return JsonResponse({"status": "ok"})

configOpen = open('staticfiles/assets/Json/config.json')
configdata = json.load(configOpen)
paramsOpen = open('staticfiles/assets/Json/inputParameters.json')
paramdata = json.load(paramsOpen)
instancebuildParameters = open('staticfiles/assets/Json/buildParameters.json')
buildData = json.load(instancebuildParameters)
instanceCount = open('staticfiles/assets/Json/instanceCount.json')
instanceData = json.load(instanceCount)

# Fsx params
region_name = configdata["region"]
s3_projectsbucket_name= configdata["projectBucket"]

# boto3 Params
config = Config(retries={"max_attempts": 15, "mode": "standard"}, signature_version="s3v4")
codebuildClient = boto3.client("codebuild", config=config, region_name=region_name)
cfnclient = boto3.client("cloudformation", config=config, region_name=region_name)
ssmclient = boto3.client("ssm", config=config,region_name=region_name)
ec2client = boto3.client("ec2", config=config,region_name=region_name)
ec2_resource = boto3.resource('ec2', config=config,region_name=region_name)
s3Resource = boto3.resource("s3",config=config, region_name=region_name)
s3Client = boto3.client("s3",config=config, region_name=region_name)
priceclient = boto3.client('pricing', region_name= region_name)
fsxClient = boto3.client('fsx',config=config, region_name=region_name)
budgetClient = boto3.client('budgets',config=config,region_name=region_name)
stsClient = boto3.client("sts",config=config,region_name=region_name)
snsClient = boto3.client("sns",config=config,region_name=region_name)
sagemakerClient = boto3.client("sagemaker",config=config,region_name=region_name)
secretsmanager_client = boto3.client("secretsmanager", config=config, region_name=region_name)
rdsClient = boto3.client("rds", config=config, region_name=region_name)
redshiftClient = boto3.client("redshift", config=config, region_name=region_name)


# WaitTime in seconds for ssm Command Execution Status
ssmMaxPolliterations = 15
ssmwaitPerIteration = 2

codeBuildProjectName = paramdata["codeBuildProjectName"]
idPrefix = paramdata["idPrefix"]
customerprefix = configdata["customerprefix"]
statusPrefix = paramdata["statusPrefix"]
sys_provider_identity =  paramdata["sysprovideridentity"]
userlist = paramdata["userlist"]
s3resourcebucket = paramdata["s3resourcebucket"]
grantorAccount = paramdata["grantorAccount"]
licid = paramdata["licid"]

# DCV Params
# possible Selection for ipSelector is 'PublicIpAddress' or 'PrivateIpAddress'
ipSelector = paramdata["ipSelector"]
dcvSessionScript = paramdata["dcvSessionScript"]
dcvSharedLocation = paramdata["dcvSharedLocation"]
PclusterDcvServerPortparam = paramdata["PclusterDcvServerPortparam"]
PclusterDcvSessionIdparam = paramdata["PclusterDcvSessionIdparam"]
PclusterDcvSessionTokenparam = paramdata["PclusterDcvSessionTokenparam"]
dcvURLTimeLimit = paramdata["dcvURLTimeLimit"]
cfnStatusPollerErrList = paramdata["cfnStatusPollerErrList"]
warpemDefExpressNodeType = paramdata['warpemDefExpressNodeType']
warpemDefebsrootdevName = paramdata['warpemDefebsrootdevName']
warpemDefebsvolSize = paramdata['warpemDefebsvolSize']

#Render Main Dashboard- Home Screen
def RenderMainDashboard(request):
    """
        This method renders the expressLaunch screen
        which is also our home screen.
        It allows the user to launch their applications which are enabled in our Numen-UI.
    """
    try:
        context={}
        appListFile = open('staticfiles/assets/Json/applications.json')
        applicationData = json.load(appListFile)
        infraFile = open('staticfiles/assets/Json/customInfrastructure.json')
        infrastructureData = json.load(infraFile)
        instanceList = open('staticfiles/assets/Json/instancesListed.json')
        instanceFamily = json.load(instanceList)
        priceInstance = open('staticfiles/assets/Json/priceInstances.json')
        instancePrice = json.load(priceInstance)
        instanceInfo = open('staticfiles/assets/Json/instanceInfo.json')
        instanceInfo = json.load(instanceInfo)
        prefixList = []
        datSetObj = s3Client.list_objects_v2(Bucket=configdata["dataBucket"],Delimiter='/')
        if datSetObj.get('CommonPrefixes') is not None:
            for obj in datSetObj.get('CommonPrefixes'):
                s3URL ="s3://"+configdata["dataBucket"]+"/"+ obj.get('Prefix')
                prefixList.append([obj.get('Prefix'),s3URL])
        context['applicationsData'] = applicationData
        context['infrastructureData'] = infrastructureData
        context['instanceFamily'] = instanceFamily
        context['instancePrices'] = instancePrice
        context['dataBucketPrefix'] = prefixList
        context['instanceInfo'] = instanceInfo["InstanceInfo"]
        #createSNSNotification(request)
        #getBudget(request)
        return JsonResponse(context)
    except Exception as e:
        logger.warning("MainDashboard-"+str(datetime.datetime.now()))
        logger.warning(e)
        error_message = {
            "error": "An error occurred while loading the dashboard.",
            "details": str(e)
        }
        return JsonResponse(error_message, status=500)

def userExists(username):
    try:
        UserPresent = False
        s3_object = s3Resource.Object(s3resourcebucket, userlist)
        line_stream = codecs.getreader("utf-8")
        for line in line_stream(s3_object.get()['Body']):
            uname=line.split(",")[0]
            if uname == username:
                UserPresent =  True
                break
        return UserPresent
    except Exception as E:
        logger.warning("userExists-"+str(datetime.datetime.now()))
        logger.warning(E)
        return False

def getUserCount():
    try:
        count = 0
        s3_object = s3Resource.Object(s3resourcebucket, userlist)
        line_stream = codecs.getreader("utf-8")
        for line in line_stream(s3_object.get()['Body']):
            uname=line.split(",")[0]
            if uname in sys_provider_identity:
                continue
            else:
                count = count + 1
        return count
    except Exception as E:
        logger.warning("getUserCount-"+str(datetime.datetime.now()))
        logger.warning(E)
        return 0

def getMaxUserEnt():
    try:
        entitlementName = "MaxUsers"
        lic_client = boto3.client("license-manager", region_name = "us-east-1") # please do not change this  for region functionality
        licArn = "arn:aws:license-manager::" + grantorAccount + ":license:" + licid
        response = lic_client.get_license_usage(LicenseArn=licArn)
        if 'LicenseUsage' in response:
            if 'EntitlementUsages' in response['LicenseUsage']:
                for ent in response['LicenseUsage']['EntitlementUsages']:
                    if ent["Name"] == entitlementName:
                        maxusage=ent["MaxCount"]
                        return (int(maxusage) )
    except Exception as E:
        logger.warning("getMaxUserEnt-"+str(datetime.datetime.now()))
        logger.warning(E)
        return 0



def getRemUserEnt():
    try:
        entitlementName = "MaxUsers"
        lic_client = boto3.client("license-manager", region_name = "us-east-1") # please do not change this  for region functionality
        licArn = "arn:aws:license-manager::" + grantorAccount + ":license:" + licid
        response = lic_client.get_license_usage(LicenseArn=licArn)
        if 'LicenseUsage' in response:
            if 'EntitlementUsages' in response['LicenseUsage']:
                for ent in response['LicenseUsage']['EntitlementUsages']:
                    if ent["Name"] == entitlementName:
                        usage=ent["ConsumedValue"]
                        maxusage=ent["MaxCount"]
                        return ( int(maxusage) - int (usage) )
    except Exception as E:
        logger.warning("getRemUserEnt-"+str(datetime.datetime.now()))
        logger.warning(E)
        return 0
        


def allow_connect_launch(user):
    try:
        if userExists(user):
            print("User "+ user  +"Found in Numen")
            return True
        else:
            print("User "+ user  +"not Found in Numen")
            max_ent = getMaxUserEnt()
            print("Max Entitlement is "+str(max_ent))
            abs_remaining = min(( max_ent -  getUserCount()), getRemUserEnt())
            print("Abs Remaining is "+str(abs_remaining))
            if abs_remaining >=1:
                return True
            else:
                return False
    except Exception as E:
        logger.warning("allow_connect_launch-"+str(datetime.datetime.now()))
        logger.warning(E)
        return False



#Render Display Resources
def renderResources(request):
    """
        This method renders the display Resources filtered by the user
    """
    try:
        userName = request.GET["username"]
        context = {}
        f = open('../scripts/result.json')
        data = json.load(f)
        for key in data.keys():
            if 'Running'== key:
                if(len(data[key]) >0):
                    #data[key] = [x for x in data[key] if x['Environment'] == configdata["environment"]]
                    data[key] = [x for x in data[key] if x['CREATEDBY'] == userName or x['sharable'] == 'true']
            else:
                if(len(data[key]) >0):
                    #data[key] = [x for x in data[key] if x['Environment'] == configdata["environment"]]
                    data[key] = [x for x in data[key] if x['CREATEDBY'] == userName]

        f.close()
        for value in data["Running"]:
            if value['CREATEDBY'] != userName and value['sharable'] == 'true':
                value["sharedInstance"] = True
                value["sharedBy"] = value['CREATEDBY'].split("@")[0]
        print(data["Running"])       
        context["data"] = data
        return JsonResponse(context)
    except Exception as e:
        logger.warning("renderResources-"+str(datetime.datetime.now()))
        logger.warning(e)

def getApplicationTemplates(request):
    """
        This function returns the application templates for express Launch
    """
    try:
        templatesFile = open('staticfiles/assets/Json/templates.json')
        templateData = json.load(templatesFile)
        applicationTemplateData = []
        applicationTemplate = templateData["templates"]
        context = {}
        for templates in applicationTemplate:
            temp=[i for i in templates['templateData'] if i["applicationName"] == request.GET["applicationName"]]
            applicationTemplateData.append(temp[0])
        context["data"] = applicationTemplateData
        return JsonResponse(context)
    except Exception as E:
        logger.warning("getApplicationTemplates-"+str(datetime.datetime.now()))
        print(E)

def appLicenceCheck(application):
    try:
        f = open('../scripts/result.json')
        f2 = open('staticfiles/assets/Json/licenceCount.json')
        data = json.load(f)
        token = 0
        data2 = json.load(f2)
        # If the application isn't in the licence file, allow it (no cap defined)
        if application not in data2:
            return True
        for x in data.keys():
            for y in data[x]:
                if application.replace(".","-") in y["StackName"]:
                    token +=1
        if token >= int(data2[application]):
            return False
        else:
            return True
    except Exception as e:
        logger.warning("appLicenceCheck-"+str(datetime.datetime.now()))
        logger.warning(e)
        return True  # allow on error — don't silently block launches


@csrf_exempt
def checkLaunch(request):
    try:
        body= json.loads(request.body)
        # Database launches (RDS/Redshift) don't have OS/nodes — approve directly
        if body.get("type") == "DATABASE":
            appLicence = appLicenceCheck(body.get('applicationName', ''))
            if appLicence:
                return JsonResponse({"canLaunch": True})
            else:
                return JsonResponse({"canLaunch": False, "exceptionMessage": "The application you have requested have no licence left."})
        osCheck = True if "os" in body.keys() else False
        packages = True if "applicationName" in body.keys()  else False
        clusterCheck =  True if body["clusterType"] != "" else False
        NodeTypeCheck = False
        appLicence = appLicenceCheck(body['applicationName'])
        if clusterCheck :
            if body["clusterType"] == "SINGLE":
                NodeTypeCheck = True if len(body.get("nodes", [])) == 1 else False
            elif body["clusterType"] == "SAGEMAKER":
                NodeTypeCheck = True if len(body.get("nodes", [])) >= 1 else False
            else:
                # PARALLEL cluster: need a master node AND at least one compute node group
                masterOk = len(body.get("nodes", [])) >= 1
                groupsOk = len(body.get("nodeGroups", [])) > 0
                NodeTypeCheck = masterOk and groupsOk
        licencecheck= True #if buildData['license']['license_status'] == "PASSED" else False
        user_name = body["email"].split("@")[0].replace(".", "_")
        userCheck = True #if allow_connect_launch(user_name) else False
        resultObj =  {}
        if osCheck and packages and clusterCheck and NodeTypeCheck and licencecheck and userCheck and appLicence:
            resultObj["canLaunch"] = True
        else:
            if osCheck == False:
                resultObj["canLaunch"] = False
                resultObj["exceptionMessage"] = "Please select valid operating system to proceed"
            elif packages == False:
                resultObj["canLaunch"] = False
                resultObj["exceptionMessage"] = "Please select Application to proceed"
            elif clusterCheck == False:
                resultObj["canLaunch"] = False
                resultObj["exceptionMessage"] = "Please select infrastructure to proceed"
            elif NodeTypeCheck == False:
                resultObj["canLaunch"] = False
                resultObj["exceptionMessage"] = "Please select infrastructure to proceed"
            elif licencecheck == False:
                resultObj["canLaunch"] = False
                resultObj["exceptionMessage"] = "No valid licence found. Please contact Numen support for licence to proceed."
            elif userCheck == False:
                resultObj["canLaunch"] = False
                resultObj["exceptionMessage"] = "MaxUsers"
            elif appLicence == False:
                resultObj["canLaunch"] = False
                resultObj["exceptionMessage"] = "The application you have requested have no licence left. Please terminate or stop one of the instance and relaunch again."
        return JsonResponse(resultObj)
    except Exception as E:
        resultObj = {}
        resultObj["canLaunch"] = False
        resultObj["exceptionMessage"] = "Work in Progress"
        resultObj["errorMess"] = str(E)
        logger.warning("appLicenceCheck-"+str(datetime.datetime.now()))
        logger.warning(E)
        return JsonResponse(resultObj)


def getInstanceList(request) :
    try:
        param = request.GET["instancename"]
        result = {}
        if param.split('-')[0] == "cpu":
                instn = getInstances(param)
        else:
                instn = getInstancesGPU(param)
        result["values"] = instn.split(':')
        return JsonResponse(result)
    except Exception as E:
        print(E)
        logger.warning("getInstanceList-"+str(datetime.datetime.now()))
        logger.warning(E)


def getInstances(param):
    try:
        fileOpen1 = open('staticfiles/assets/Json/instanceListedPC.json')
        instanceFamily = json.load(fileOpen1)
        instancesList=instanceFamily['InstancesList']
        params = param.split('-')
        instances = [i[params[1]] for i in instancesList if list(i.keys())[0] == params[1]][0]
        avg = round(len(instances)/2)
        inst = ''
        if params[2] == 'small':
            inst = instances[0]+':'+instances[1]+':'+instances[2]
        elif params[2] == 'medium':
            inst = instances[avg-1]+':'+instances[avg]+':'+instances[avg+1]
        elif params[2] == 'large':
            inst = instances[len(instances)-3]+':'+instances[len(instances)-2]+':'+instances[len(instances)-1]
        return str(inst)
    except Exception as e:
        logger.warning("getInstances-"+str(datetime.datetime.now()))
        logger.warning(e)

def getInstancesGPU(param):
    try:
        fileOpen1 = open('staticfiles/assets/Json/instancesListedPC.json')
        instanceFamily = json.load(fileOpen1)
        instancesList=instanceFamily['InstancesList']
        params = param.split('-')
        instances = [i[params[1]] for i in instancesList if list(i.keys())[0] == params[1]][0]
        fileOpen2 = open('staticfiles/assets/Json/instanceInfo.json')
        instancesInfo = json.load(fileOpen2)
        instancesInfo = instancesInfo["InstanceInfo"]
        instaL = []
        retInstances = ''
        for i in instances:
            inst = [j["InstanceType"] for j in instancesInfo if j["InstanceType"] == i and j["GpuCount"] == int(params[2])]
            if len(inst) >0:
                instaL.append(inst[0])
        if len(instaL) > 3 :
            retInstances = instaL[0]+":"+instaL[1]+":"+instaL[2]
        else:
            retInstances = ":".join([str(elem) for i,elem in enumerate(instaL)])
        return str(retInstances)
    except Exception as e:
        logger.warning("getInstancesGPU-"+str(datetime.datetime.now()))
        logger.warning(e)
    
def startCodeBuild(project, envParamsList):
    """
        This method related to the launch and helps the python application to start the code build in AWS
    """
    response = codebuildClient.start_build(
        projectName=project, environmentVariablesOverride=envParamsList
    )
    return response

def getProjectDetails(projectNameList):
        response = codebuildClient.batch_get_projects(names=projectNameList)
        return response

def getCustomAMI(os, packages=None):
    """
    Fetch the AMI id for the given OS (and optionally application package name).
    Lookup order:
      1. Entry whose 'packages' list contains the requested package AND whose 'os' matches.
         Comparison is case-insensitive on both sides so "Linux" matches "linux" in JSON.
      2. Fallback: entry whose 'packages' list is empty (or absent) AND whose 'os' matches —
         this is the default/GPU AMI for that OS, preserving legacy behaviour for all
         existing apps that don't have a dedicated packages entry.
    """
    try:
        fileOpen = open('staticfiles/assets/Json/amiImages.json')
        data = json.load(fileOpen)
        os_lower = os.lower()
        default_ami = "Fail"
        # Pass 1 — package-specific match (highest priority, case-insensitive)
        if packages:
            packages_lower = packages.lower()
            for i in data["Applications"]:
                json_pkgs_lower = [p.lower() for p in i.get("packages", [])]
                if os_lower == i["os"].lower() and packages_lower in json_pkgs_lower:
                    return i["ami"]
        # Pass 2 — OS default: entry with empty/absent packages = default AMI for that OS
        for i in data["Applications"]:
            if os_lower == i["os"].lower() and not i.get("packages"):
                default_ami = i["ami"]
        if default_ami == "Fail":
            logger.warning(
                "getCustomAMI: no AMI found for os=%s packages=%s — check amiImages.json",
                os, packages
            )
        return default_ami
    except Exception as E:
        logger.warning("getCustomAMI-"+str(datetime.datetime.now()))
        logger.warning(E)
        return "Fail"

def getCloudformationStackStatus(StackName):
    """
        This fetches the stack information for a specific stack name
    """
    try:
        response = cfnclient.describe_stacks(StackName=StackName)
        return response
    except Exception as e:
        logger.warning("getCloudformationStackStatus-"+str(datetime.datetime.now()))
        logger.warning(e)

def StackExists(StackName):
    """
        A boolean method which informs if the stack exists in AWS
    """
    try:
        response = cfnclient.describe_stacks(StackName=StackName)
        return True
    except ClientError:
        return False


def getCloudformationStackResource(StackName, ResourceId):
    """
        This fetches the cloud formation stack with stackname and resource id
    """
    try:
        response = cfnclient.describe_stack_resource(
            StackName=StackName, LogicalResourceId=ResourceId
        )
        return response
    except Exception as e:
        #print(e)
        logger.warning("getCloudformationStackResource-"+str(datetime.datetime.now()))
        logger.warning(e)
        return "Undefined"


def getBuildDetails(BuildId):
    response = codebuildClient.batch_get_builds(ids=[BuildId])
    return response

def getssmResults(instanceid, DocName, CommandList):
    try:
        response = ssmclient.send_command(
            InstanceIds=[instanceid],
            DocumentName=DocName,
            Parameters={"commands": [CommandList]},
        )
        command_id = response["Command"]["CommandId"]
        for i in range(ssmMaxPolliterations):
            time.sleep(ssmwaitPerIteration)
            output = ssmclient.get_command_invocation(
                CommandId=command_id, InstanceId=instanceid
            )
            if output["Status"] == "Success" and output["ResponseCode"] == 0:
                return (
                    "Success"
                    if not output["StandardOutputContent"]
                    else output["StandardOutputContent"]
                )
            else:
                continue
    except Exception as E:
        logger.warning("getssmResults-"+str(datetime.datetime.now()))
        logger.warning(E)


def getec2Details(InstanceID):
    try:
        response = ec2client.describe_instances(InstanceIds=[InstanceID])
        return response
    except Exception as E:
        logger.warning("getec2Details-"+str(datetime.datetime.now()))
        logger.warning(E)
        return "NULL"

def getUniqId(N):
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=N))


def getnicAttr(Attribute, nicId):
    response = ec2client.describe_network_interface_attribute(
        Attribute=Attribute, NetworkInterfaceId=nicId
    )
    return response

def builddcvURL(tokenString, hostname):
    componentsList = tokenString.split(" ")
    for i in range(len(componentsList)):
        if PclusterDcvServerPortparam in componentsList[i]:
            dcvPort = componentsList[i].split("=")[-1].strip()
        elif PclusterDcvSessionIdparam in componentsList[i]:
            dcvSessionId = componentsList[i].split("=")[-1].strip()
        elif PclusterDcvSessionTokenparam in componentsList[i]:
            dcvSessionToken = componentsList[i].split("=")[-1].strip()
    return (
        "https://"
        + hostname
        + ":"
        + dcvPort
        + "?authToken="
        + dcvSessionToken
        + "#"
        + dcvSessionId
    )


def deletecfnstack(stackName):
    try:

        fileSystemId = "NotExists"
        fileSystemId= getfsxId(stackName)
        #print(fileSystemId)
        response = cfnclient.delete_stack(StackName=stackName,RetainResources=[])
        if fileSystemId != "NotExists":
            response2 = fsxClient.delete_file_system(FileSystemId=fileSystemId)
        return response
    except Exception as E:
        logger.warning("DeleteCFn-"+str(datetime.datetime.now()))
        logger.warning(E)


def getfsxId(stackname):
    try:
        sName = ""
        cfnStatusresponse = getCloudformationStackStatus(stackname)
        if 'Tags' in cfnStatusresponse["Stacks"][0].keys():
                    for stack in cfnStatusresponse["Stacks"][0]["Tags"]:
                        if stack["Key"] == "CUSTOMNAME":
                           sName = stack["Value"] 
        fsxid = "NotExists"
        response=fsxClient.describe_file_systems()
        response = response["FileSystems"]
        for i in response:
            for j in i["Tags"]:
                if j["Key"]== 'FSXName' and j["Value"] == sName:
                    fsxid = i["FileSystemId"]
                    break
            if fsxid != "NotExists":
                break
        return fsxid
    except Exception as E:
        logger.warning("GetFsxId-"+str(datetime.datetime.now()))
        logger.warning(E)
        return fsxid

@csrf_exempt
def deleteResourceButton(request):
    try:
        status = False
        body= json.loads(request.body)
        StackName = body["stackName"]
        if "instanceId" in body.keys():
            instanceId = body["instanceId"]
            machineAttrs=ec2_resource.Instance(instanceId)
            response = machineAttrs.state['Name']
            if response == 'running':
                if 'warpem' in StackName:
                    retValue =  getssmResults(instanceId, "AWS-RunPowerShellScript", "python C:\\Numen\\temp\\ImageBuilder\\cleanup_listener.py")
                else:
                    retValue = getssmResults(instanceId, "AWS-RunShellScript", f"bash /opt/numen/scripts/nicedcv/cleanup_listener.sh")
                response = deletecfnstack(StackName)
                if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
                    status = True
                    removeStackId(StackName)
            elif response == 'stopped':
                response = ec2client.start_instances(InstanceIds=[instanceId])
                time.sleep(5)
                if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
                    if 'warpem' in StackName:
                        retValue =  getssmResults(instanceId, "AWS-RunPowerShellScript", "python C:\\Numen\\temp\\ImageBuilder\\cleanup_listener.py")
                    else:
                        retValue = getssmResults(instanceId, "AWS-RunShellScript", f"bash /opt/numen/scripts/nicedcv/cleanup_listener.sh")
                    response = deletecfnstack(StackName)
                    if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
                        status = True
                        removeStackId(StackName)
        else:
            response = deletecfnstack(StackName)
            if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
                status = True
                removeStackId(StackName)
        obj_dict = {
            "status":status
           }
        return JsonResponse(obj_dict)
    except Exception as E :
        logger.warning("DeleteEc2-"+str(datetime.datetime.now()))
        logger.warning(E)

#Start the Ec2Instance
@csrf_exempt
def startResourceButton(request):
    try:
        status = False
        body = json.loads(request.body)
        instanceId    = body["instanceId"]
        stackName     = body["stackName"]
        resource_type = body.get("resourceType", "").upper()

        if resource_type == "RDS":
            response = rdsClient.start_db_instance(DBInstanceIdentifier=instanceId)
            if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
                status = True

        elif resource_type == "REDSHIFT":
            response = redshiftClient.resume_cluster(ClusterIdentifier=instanceId)
            if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
                status = True

        else:
            # Default: EC2 instance
            response = ec2client.start_instances(InstanceIds=[instanceId])
            if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
                status = True

        return JsonResponse({"status": status})
    except Exception as E:
        logger.warning("StartResourceButton-"+str(datetime.datetime.now()))
        logger.warning(E)
        return JsonResponse({"status": False, "error": str(E)})

#Stop the Ec2Instance
@csrf_exempt
def stopResourceButton(request):
    try:
        status = False
        body = json.loads(request.body)
        instanceId    = body["instanceId"]
        stackName     = body["stackName"]
        resource_type = body.get("resourceType", "").upper()

        if resource_type == "RDS":
            response = rdsClient.stop_db_instance(DBInstanceIdentifier=instanceId)
            if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
                status = True

        elif resource_type == "REDSHIFT":
            response = redshiftClient.pause_cluster(ClusterIdentifier=instanceId)
            if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
                status = True

        else:
            # Default: EC2 instance
            response = ec2client.stop_instances(InstanceIds=[instanceId])
            if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
                status = True
                timeNow = datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                ec2client.create_tags(
                    Resources=[instanceId],
                    Tags=[{'Key': 'StoppedSince', 'Value': timeNow}])

        return JsonResponse({"status": status})
    except Exception as E:
        logger.warning("StopResource-"+str(datetime.datetime.now()))
        logger.warning(E)
        return JsonResponse({"status": False, "error": str(E)})

#TerminateResourceButton
@csrf_exempt
def terminateResourceButton(request):
    try:
        body= json.loads(request.body)
        instanceId = body["instanceId"]
        stackName = body["stackName"]
        response = ec2client.terminate_instances(InstanceIds=[instanceId])
        if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
            return renderResources(request)
    except Exception as E :
        logger.warning("TerminateResourceButton-"+str(datetime.datetime.now()))
        logger.warning(E)

#RebootEC2Instance
@csrf_exempt
def rebootResourceButton(request):
    try:
        status = False
        body= json.loads(request.body)
        instanceId = body["instanceId"]
        stackName = body["stackName"]
        response = ec2client.reboot_instances(InstanceIds=[instanceId])
        if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
            status = True
        obj_dict = {
            "status":status
           }
        return JsonResponse(obj_dict)
    except Exception as E :
        logger.warning("RebootResourceButton-"+str(datetime.datetime.now()))
        logger.warning(E)

#Building DCV URL
@csrf_exempt
def connectEC2Machine(request):
    try:
        body= json.loads(request.body)
        instanceId = body["instanceId"]
        alb = body["alb"]
        stackName = body["stackName"]
        print(instanceId,alb,stackName)

        # ── SageMaker Notebook: return a pre-signed Jupyter URL ──────────────
        # Notebook instance names are stored prefixed with "sm-" in result.json
        if instanceId.startswith("sm-"):
            smResponse = sagemakerClient.create_presigned_notebook_instance_url(
                NotebookInstanceName=instanceId,
                SessionExpirationDurationInSeconds=1800
            )
            obj_dict = {
                "dcvInfo":  smResponse["AuthorizedUrl"],
                "smType":   True,
                "Status":   "SageMaker Notebook URL ready. Link expires in 30 minutes."
            }
            return JsonResponse(obj_dict)
        # ─────────────────────────────────────────────────────────────────────

        machineAttrs = getec2Details(instanceId)
        tags = machineAttrs["Reservations"][0]["Instances"][0]['Tags']
        tagValue = [i['Value'] for i in tags if i['Key'] == 'Port']
        stackName = [i['Value'] for i in tags if i['Key'] == 'CUSTOMNAME'][0]
        resourcebucket = [i['Value'] for i in tags if i['Key'] == 'RESOURCEBUCKET'][0]
        PriorityValue = [i['Value'] for i in tags if i['Key'] == 'PriorityOrder']
        Email = body["email"]
        Nodeuser = Email.split("@")[0].replace(".", "_")
        """ if not allow_connect_launch(Nodeuser):
            obj_dict = {"Status": "max_userlicense_count" }
            print(obj_dict)
            return JsonResponse(obj_dict) """

        if "warpem" in stackName:
            checkuser = getssmResults(instanceId, "AWS-RunPowerShellScript", "powershell.exe -File C:\\Numen\\temp\\ImageBuilder\\create_user.ps1 "+Nodeuser).strip()
            url = getssmResults(instanceId, "AWS-RunPowerShellScript", "powershell.exe -File C:\\Numen\\temp\\ImageBuilder\\create_dcvsession.ps1 "+Nodeuser+" "+alb).strip()
            occ_locatorval = 3
            dec_list = [m.start() for m in re.finditer(r"/", url)]
            if len(dec_list)>= occ_locatorval:
                queryparam=url[dec_list[occ_locatorval-1]+1:]
                obj_dict = {
                    "dcvInfo": "https://"+alb.split("//")[-1].split(":")[0]+":"+tagValue[0]+"/"+queryparam,
                    "Status": "Workflow Completed, Please Click on below link within "
                    + dcvURLTimeLimit
                    + " Seconds to access the Node",
                }
            return JsonResponse(obj_dict)
        application = ""
        if "sn" in stackName:
            application = stackName.split('-')[1]
        else:
            application = stackName.split('-')[0]
        if "cryoSPARC" in stackName:
            checkuser = getssmResults(instanceId, "AWS-RunShellScript", f"bash /opt/numen/scripts/nicedcv/dcvuser.sh {Nodeuser} {Email} true {application} {resourcebucket}").strip()
            obj_dict = {
                            "dcvInfo": "https://"+alb.split("//")[-1].split(":")[0]+":"+tagValue[0]+"/",
                            "Status": "Workflow Completed, Please Click on below link within "
                            + dcvURLTimeLimit
                            + " Seconds to access the Node",
                        }
            print(obj_dict)
            return JsonResponse(obj_dict)
        else:
            checkuser = getssmResults(instanceId, "AWS-RunShellScript", f"bash /opt/numen/scripts/nicedcv/dcvuser.sh {Nodeuser} {Email} false {application} {resourcebucket}").strip()
            url =  getssmResults(instanceId, "AWS-RunShellScript", f"bash /opt/numen/scripts/nicedcv/dcvlink.sh {Nodeuser} {stackName}").strip()
            occ_locatorval = 3
            dec_list = [m.start() for m in re.finditer(r"/", url)]
            if len(dec_list)>= occ_locatorval:
                queryparam=url[dec_list[occ_locatorval-1]+1:]
            obj_dict = {
                            "dcvInfo": "https://"+alb.split("//")[-1].split(":")[0]+":"+tagValue[0]+"/"+queryparam,
                            "Status": "Workflow Completed, Please Click on below link within "
                            + dcvURLTimeLimit
                            + " Seconds to access the Node",
                        }
            print(obj_dict)
            return JsonResponse(obj_dict)
    except Exception as e:
        logger.warning("connectEC2Machine-"+str(datetime.datetime.now()))
        logger.warning("connectEC2Machine: %s", str(e))
        return JsonResponse({"dcvInfo": None, "Status": "Error: " + str(e)}, status=500)


def getInstancetag(instanceId, tagKey):
    try:
        response = ec2client.describe_tags(
                    Filters=[
                        {
                            'Name': 'resource-id',
                            'Values': [
                                instanceId,
                            ],
                        },
                    ],
        )
    except Exception as E:
        logger.warning("getInstancetag-"+str(datetime.datetime.now()))
        logger.warning(E)

def getLicencestatus():
    """
        This checks the licencing for the client to launch application using Numen
    """
    try:
        status = "NULL"
        EnvVars = getProjectDetails([codeBuildProjectName])["projects"][0]["environment"][
                "environmentVariables"
            ]
        for env in EnvVars:
                if env["name"] == "lic_status":
                   print(env["value"])
                   status = env["value"]
                   break;
        obj_dict = {
            "status":status
           }
        return status
    except Exception as E:
        logger.warning("getLicencestatus-"+str(datetime.datetime.now()))
        logger.warning(E)

@csrf_exempt
def shareResourceButton(request):
    """
        This method enables the user to share the instance dcv with other across the organisation
    """
    try:
        status = False
        body= json.loads(request.body)
        instanceId = body["instanceId"]
        stackName = body["stackName"]
        response = ec2client.create_tags(
                Resources=[instanceId,],
                Tags=[{'Key': 'sharable','Value': 'true'},{'Key': 'shareWith','Value': 'ALL'}])
        if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
            status = True
        obj_dict = {
            "status":status
           }
        return JsonResponse(obj_dict) 
    except Exception as E:
        logger.warning("ShareResourceButton-"+str(datetime.datetime.now()))
        logger.warning(E)


@csrf_exempt
def unShareResourceButton(request):
    """
        This method enables the user to unshare the instance dcv with other across the organisation
    """
    try:
        status = False
        body= json.loads(request.body)
        instanceId = body["instanceId"]
        stackName = body["stackName"]
        response = ec2client.create_tags(
            Resources=[
                instanceId,
            ],
            Tags=[
                {
                    'Key': 'sharable',
                    'Value': 'false'
                }
            ])
        if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
            status = True
        obj_dict = {
            "status":status
           }
        return JsonResponse(obj_dict)
    except Exception as E:
        logger.warning("UnShareResourceButton-"+str(datetime.datetime.now()))
        logger.warning(E)

#Budgets
def getBudget(request):
    try:
        accountId=stsClient.get_caller_identity()["Account"]
        userName = request.GET["username"]
        response = budgetClient.describe_budgets(AccountId=accountId, MaxResults= 99)
        fileOpen = open('../django_forms/staticfiles/assets/Json/createBudget.json')
        data = json.load(fileOpen)
        budgetLimit = data["BudgetParameters"]["BudgetLimit"]
        calculatedSpend = 0
        forecastedSpend = 0
        budgetDetails = {}
        budgetDetails["snsCreated"] = False
        if "Budgets" in response.keys():
            currentBudget=[i for i in response["Budgets"] if i['BudgetName'] == userName.split('.')[0]+"'s "+ configdata["environment"] +" Monthly Budget"]
            if len(currentBudget) > 0:
                if 'CalculatedSpend' in currentBudget[0].keys():
                    budgetLimit = int(round(float(currentBudget[0]['BudgetLimit']['Amount']),0))
                    calculatedSpend = int(round(float(currentBudget[0]['CalculatedSpend']['ActualSpend']['Amount']),0))
                    if "ForecastedSpend" in currentBudget[0]['CalculatedSpend'].keys():
                        forecastedSpend = int(round(float(currentBudget[0]['CalculatedSpend']['ForecastedSpend']['Amount']),0))
                    budgetDetails["budgetLimt"] = budgetLimit
                    budgetDetails["calculatesSpend"] = calculatedSpend
                    budgetDetails["forecastedSpend"] = forecastedSpend
            else:
                # Try to create a user budget; fall back to $0 if creation fails
                created = createBudget(data, request, userName, accountId)
                if created and isinstance(created, dict):
                    budgetDetails.update(created)
                else:
                    budgetDetails["budgetLimt"] = int(budgetLimit) if budgetLimit else 0
                    budgetDetails["calculatesSpend"] = 0
                    budgetDetails["forecastedSpend"] = 0
        else:
            budgetDetails["budgetLimt"] = int(budgetLimit) if budgetLimit else 0
            budgetDetails["calculatesSpend"] = 0
            budgetDetails["forecastedSpend"] = 0
        # --- Active instance count + real spend from result.json ---
        try:
            result_path = os.path.join(os.path.dirname(__file__), '..', '..', 'scripts', 'result.json')
            with open(result_path) as rf:
                result_data = json.load(rf)

            def _match_user(inst):
                return inst.get('CREATEDBY', '').lower() == userName.lower()

            # Active = Running / Provisioning / Inprogress (for count display)
            active_instances = []
            for bucket in ('Running', 'Provisioning', 'Inprogress'):
                active_instances += [i for i in result_data.get(bucket, []) if _match_user(i)]

            # Cost = all non-terminated instances including Stopped
            all_user_instances = active_instances[:]
            for bucket in ('Stopped',):
                all_user_instances += [i for i in result_data.get(bucket, []) if _match_user(i)]

            # Fallback: if no instances matched this email, use ALL instances
            # (shared/demo account where CREATEDBY may differ from login email)
            if not all_user_instances:
                all_instances_flat = []
                for bucket in ('Running', 'Provisioning', 'Inprogress', 'Stopped'):
                    all_instances_flat += result_data.get(bucket, [])
                active_instances  = [i for i in all_instances_flat if i in result_data.get('Running', []) + result_data.get('Provisioning', []) + result_data.get('Inprogress', [])]
                active_instances  = result_data.get('Running', []) + result_data.get('Provisioning', []) + result_data.get('Inprogress', [])
                all_user_instances = all_instances_flat

            budgetDetails['instance_count'] = len(
                result_data.get('Running', []) + result_data.get('Provisioning', []) + result_data.get('Inprogress', [])
            )

            instance_spend = int(round(sum(
                float(i.get('costUtilised', 0) or 0) for i in all_user_instances
            ), 0))

            # Use instance spend when AWS Budgets returns 0 for this user
            if budgetDetails.get('calculatesSpend', 0) == 0 and instance_spend > 0:
                budgetDetails['calculatesSpend'] = instance_spend
                budgetDetails.setdefault('budgetLimt', int(budgetLimit) if budgetLimit else 500)
                budgetDetails.setdefault('forecastedSpend', instance_spend)

            # Always include remaining so frontend can display it
            budgetDetails['remaining'] = max(0, budgetDetails.get('budgetLimt', 500) - budgetDetails.get('calculatesSpend', 0))
        except Exception as ex:
            logger.warning(f"getBudget result.json: {ex}")
            budgetDetails['instance_count'] = 0
            budgetDetails.setdefault('remaining', max(0, budgetDetails.get('budgetLimt', 500) - budgetDetails.get('calculatesSpend', 0)))

        return JsonResponse(budgetDetails)
    except Exception as E:
        logger.warning("getBudget-"+str(datetime.datetime.now()))
        logger.warning(E)
        print(E)
        error_message = {
            "error": "An error occurred while loading the dashboard.",
            "details": str(E)
        }
        return JsonResponse(error_message, status=500)


@csrf_exempt
def updateBudget(request):
    """Update the monthly budget limit for a user."""
    try:
        body = json.loads(request.body)
        userName = body.get("username", "")
        newLimit = str(int(float(body.get("budgetLimit", 500))))
        accountId = stsClient.get_caller_identity()["Account"]
        budgetName = userName.split('.')[0] + "'s " + configdata["environment"] + " Monthly Budget"
        # Check if budget exists
        response = budgetClient.describe_budgets(AccountId=accountId, MaxResults=99)
        existing = [b for b in response.get("Budgets", []) if b["BudgetName"] == budgetName]
        if existing:
            budgetClient.update_budget(
                AccountId=accountId,
                NewBudget={
                    **existing[0],
                    "BudgetLimit": {"Amount": newLimit, "Unit": "USD"},
                }
            )
        else:
            # No personal budget yet — just return the new limit (will be created on next describe)
            pass
        return JsonResponse({"budgetLimt": int(newLimit), "calculatesSpend": 0, "forecastedSpend": 0, "snsCreated": False})
    except Exception as E:
        logger.warning("updateBudget-" + str(datetime.datetime.now()))
        logger.warning(E)
        return JsonResponse({"error": str(E)}, status=500)


def createBudget(data,request,userName,accountId):
    """
        This creates the budget.
        Input:
        data: data to create budget
        accountId: id of the account
    """
    try:
        snsARN = createSNSNotification(userName)
        response = budgetClient.create_budget(
                    AccountId=accountId,
                    Budget={
                        'BudgetName': userName.split('.')[0]+"'s "+ configdata["environment"] +" Monthly Budget",
                        'BudgetLimit': {
                            'Amount': data["BudgetParameters"]["BudgetLimit"],
                            'Unit': 'USD'
                        },
                        'CostFilters': {'Service': ['Amazon Elastic Compute Cloud - Compute', 'EC2-Other', 'FSx'], 'TagKeyValue': ['user:CREATEDBY$'+userName,'user:Environment$'+configdata["environment"]]},
                        'CostTypes': {
                            'IncludeTax': True,
                            'IncludeSubscription': True,
                            'UseBlended': False,
                            'IncludeRecurring':True
                        },
                        'TimeUnit': data["BudgetParameters"]["TimeUnit"],
                        'TimePeriod': {
                            'Start': datetime.datetime(datetime.date.today().year, datetime.date.today().month, datetime.date.today().day),

                        },
                        'CalculatedSpend': {
                            'ActualSpend': {
                                'Amount': '1.75',
                                'Unit': 'USD'
                            },
                            'ForecastedSpend': {
                                'Amount': '1.75',
                                'Unit': 'USD'
                            }
                        },
                        'BudgetType': 'COST'
                    },
                    NotificationsWithSubscribers=[
                    {
                        'Notification': {
                            'NotificationType': 'ACTUAL',
                            'ComparisonOperator': 'GREATER_THAN',
                            'Threshold': 90
                        },
                        'Subscribers': [
                                            {
                                                "SubscriptionType": "EMAIL",
                                                "Address": userName
                                            },
                                            {
                                                'SubscriptionType': 'SNS',
                                                'Address': snsARN["SNSTopicUser"]
                                            }
                                        ]
                    },
                    {
                        'Notification': {
                            'NotificationType': 'ACTUAL',
                            'ComparisonOperator': 'GREATER_THAN',
                            'Threshold': 70
                        },
                        'Subscribers': [
                                            {
                                                "SubscriptionType": "EMAIL",
                                                "Address": userName
                                            },
                                            {
                                                'SubscriptionType': 'SNS',
                                                'Address': snsARN["SNSTopicUser"]
                                            }
                                        ]
                    }
                    ]
                )
        budgetDetails = {}
        budgetDetails["snsCreated"] = True
        if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
            response = budgetClient.describe_budgets(AccountId=accountId, MaxResults= 99)
            fileOpen = open('../django_forms/staticfiles/assets/Json/createBudget.json')
            data = json.load(fileOpen)
            budgetLimit = data["BudgetParameters"]["BudgetLimit"]
            calculatedSpend = 0
            forecastedSpend = 0
            if "Budgets" in response.keys():
                currentBudget=[i for i in response["Budgets"] if i['BudgetName'] == userName.split('.')[0]+"'s "+ configdata["environment"] +" Monthly Budget"]
                if len(currentBudget) > 0:
                    if 'CalculatedSpend' in currentBudget[0].keys():
                        budgetLimit = int(round(float(currentBudget[0]['BudgetLimit']['Amount']),0))
                        calculatedSpend = int(round(float(currentBudget[0]['CalculatedSpend']['ActualSpend']['Amount']),0))
                        if "ForecastedSpend" in currentBudget[0]['CalculatedSpend'].keys():
                            forecastedSpend = int(round(float(currentBudget[0]['CalculatedSpend']['ForecastedSpend']['Amount'],0)))
                        budgetDetails["budgetLimt"] = budgetLimit
                        budgetDetails["calculatesSpend"] = calculatedSpend
                        budgetDetails["forecastedSpend"] = forecastedSpend
            return budgetDetails
    except Exception as E:
        logger.warning("createBudget-"+str(datetime.datetime.now()))
        logger.warning(E)

def createSNSNotification(userName):
    try:
        snsDetails = snsexist(userName)
        if snsDetails["snsExists"] == False:
            numenSNS=customerprefix+'sns-'+userName.split('@')[0]
            numenSNS=numenSNS.replace('.','-')
            snsresponse = snsClient.create_topic(
                Name=numenSNS,
                Attributes={
                    'DisplayName': numenSNS
                },
            )
            if snsresponse["ResponseMetadata"]["HTTPStatusCode"] == 200:
                response = snsClient.subscribe(
                            TopicArn=snsresponse["TopicArn"],
                            Protocol='email',
                            Endpoint= userName,
                            ReturnSubscriptionArn=True
                        )
                snsDetails["SNSTopicUser"] = snsresponse["TopicArn"]
        return snsDetails
    except Exception as E:
        logger.warning("createSNSNotification-"+str(datetime.datetime.now()))
        logger.warning(E)


def snsexist(userName):
    try:
        snsDetails = {}
        response = snsClient.list_topics()
        describe_result = response["Topics"]
        accountId=stsClient.get_caller_identity()["Account"]
        while "NextToken" in response:
            response = snsClient.list_topics(NextToken=response["NextToken"])
            describe_result.extend(response["Topics"])
        print(describe_result)
        topicArn = 'arn:aws:sns:'+region_name+':'+accountId+':'+ customerprefix +'sns-'+userName.split('@')[0].replace('.','-')
        response = [i["TopicArn"] for i in describe_result if i["TopicArn"] == topicArn]
        if len(response) > 0 :
            snsDetails["snsExists"] = True
            snsDetails["SNSTopicUser"] = response[0]
            return snsDetails
        else:
            snsDetails["snsExists"] = False
            return snsDetails
    except Exception as E:
        logger.warning("createSNSNotification-"+str(datetime.datetime.now()))
        logger.warning(E)
        print("createSNS",E)

@csrf_exempt
def withoutCodeBuild(request):
    try:
        body = json.loads(request.body)
        stackID = getStackId()
        body["stackID"] = stackID

        # --- Database launches (RDS / Redshift) ---
        user_tags = body.get("userTags", [])
        if body["clusterType"] == "RDS":
            rdsStackName = "numen-rds-" + str(stackID)
            body["stackName"] = rdsStackName
            buildParameters = launchRDS(body)
            response = rdsBuild(buildParameters, rdsStackName, body["email"], user_tags=user_tags)
            responseObject = {"status": response["StackId"]}
            return JsonResponse(responseObject)

        if body["clusterType"] == "REDSHIFT":
            rsStackName = "numen-rs-" + str(stackID)
            body["stackName"] = rsStackName
            buildParameters = launchRedshift(body)
            response = redshiftBuild(buildParameters, rsStackName, body["email"], user_tags=user_tags)
            responseObject = {"status": response["StackId"]}
            return JsonResponse(responseObject)

        # --- Compute launches ---
        stackName = body["applicationName"].replace('.', '-') + "-" + body["os"].replace('.', '-') + "-" + idPrefix + getUniqId(4)
        body["stackName"] = stackName
        FileSystem = ""
        if len(body.get("volumes", [])) > 0:
            fsxSize = [i["size"] for i in body["volumes"] if i["type"] == "FSX"]
            if len(fsxSize) > 0:
                FileSystem = fsxSize[0]
                createFsxForInstance(body, fsxSize[0], stackName, str(stackID))

        if body["clusterType"] == "SAGEMAKER":
            buildParameters = launchSageMaker(body)
            smStackName = configdata.get("smstackprefix", "SM-EC2-CURIA-") + str(stackID)
            response = sageMakerBuild(buildParameters, smStackName)
            responseObject = {"status": response["StackId"]}
            return JsonResponse(responseObject)
        elif body["clusterType"] == "SINGLE":
            parameterObj = {}
            buildParameters = launchSingleNode(body)
            print(buildParameters)
            if "alinux" in body["os"]:
                buildParameters["EBSROOTDEVNAME"] = "/dev/xvda"
            parametersIns = []
            for key, value in buildParameters.items():
                parametersIns.append({'ParameterKey': key, 'ParameterValue': value})
            instancetags = [
                {'Key': 'Platform', 'Value': 'Numen'},
                {'Key': 'CREATEDBY', 'Value': body["email"]},
                {'Key': 'RESOURCEBUCKET', 'Value': buildData["singleNode"]['Bucket']},
                {'Key': 'IdleStop', 'Value': str(body["idleTimeout"]["value"])},
                {'Key': 'CUSTOMNAME', 'Value': buildParameters["ResId"]},
                {'Key': 'Environment', 'Value': configdata["environment"]}
            ]
            # Merge user-defined custom tags from agent or wizard
            for ut in body.get("userTags", []):
                if ut.get("Key") and ut.get("Value"):
                    instancetags.append({'Key': ut["Key"], 'Value': str(ut["Value"])})
            parameterObj["stackName"] = configdata["snstackprefix"] + str(stackID)
            parameterObj["InstanceTags"] = instancetags
            parameterObj["envVariables"] = parametersIns
            response = singleNodeBuild(parameterObj, body["os"])
            responseObject = {"status": response["StackId"]}
            return JsonResponse(responseObject)
        else:
            envvalues = launchParallelCluster(body)
            if envvalues is None:
                return JsonResponse({"status": "error", "message": "Failed to build parallel cluster parameters"}, status=500)
            if FileSystem != "":
                envvalues["FILESYSTEM"] = "FSX:" + str(FileSystem)
            stackName = configdata["pcstackprefix"] + str(stackID)
        rc = parallelNodeBuild(envvalues, stackName)

            # pcluster success output contains cloudformationStackStatus; anything else is an error
        if rc and ("cloudformationStackStatus" in rc or "cloudformationStackArn" in rc):
            responseObject = {"status": rc}
        else:
            logger.warning("withoutCodeBuild-pcluster failed for stack %s: %s", stackName, rc)
            return JsonResponse({"status": "error", "message": rc or "pcluster create-cluster failed with no output"}, status=500)
        return JsonResponse(responseObject)
    except Exception as E:
        print(E)
        logger.warning("withoutCodeBuild-" + str(datetime.datetime.now()))
        logger.warning(E)
        return JsonResponse({"status": "error", "message": str(E)}, status=500)



def getStackId():
     try:
        stackID = 000
        if(len(instanceData["instanceID"]) < 999):
            stackID = len(instanceData["instanceID"])+1
            stackID = "{:03d}".format(stackID)
            if checkStackId(stackID):
                stackID = stackID
            else:
                stackID = len(instanceData["instanceID"])+2
                stackID = "{:03d}".format(stackID)
            instanceData["instanceID"].append(stackID)
            with open("staticfiles/assets/Json/instanceCount.json","w") as outfile:
                json.dump(instanceData, outfile,default=str)
        return stackID    
     except Exception as E:
        logger.warning("getStackId-"+str(datetime.datetime.now()))
        logger.warning(E)

def checkStackId(stackID):
    try:
        response = cfnclient.list_stacks()
        stackSummary = response["StackSummaries"] 
        stackName =  "NUMEN-"+stackID
        while "NextToken" in response:
            response = cfnclient.list_stacks(NextToken=response["NextToken"])
            stackSummary.extend(response["StackSummaries"])
        stackListName = [item["StackName"] for item in stackSummary if stackName.lower() in item["StackName"].lower()]
        if len(stackListName) > 0 :
            return False
        else:
            return True
    except Exception as E:
        print(E)



def launchSingleNode(body):
    try:
        Packages = body["applicationName"]
        if body["os"] != "windows":
            # Copy to avoid mutating the shared config dict across concurrent requests
            buildParameters = dict(buildData["singleNode"])
            buildParameters["PACKAGES"] = Packages
            buildParameters["instancename"] = configdata["instanceidprefix"] + str(body["stackID"])
        else:
            buildParameters = dict(buildData["sNwindows"])
            buildParameters["instancename"] = configdata["instanceidprefix"] + str(body["stackID"])
        resId = "sn-" + body["stackName"]
        buildParameters["ResId"] = resId
        ami = getCustomAMI(body["os"], packages=body.get("applicationName"))
        if ami == "Fail":
            raise ValueError(
                f"No AMI found for OS='{body['os']}' application='{body.get('applicationName')}'. "
                "Please check amiImages.json configuration."
            )
        buildParameters["ImageId"] = ami
        # Pass selected tool names as SelectedPackages to the CFT.
        # The CFT userdata reads this parameter and installs each tool on boot.
        selected_tools = body.get("packages", [])
        if selected_tools:
            buildParameters["SelectedPackages"] = ",".join(selected_tools)
        if len(body.get("volumes", [])) > 0:
            ebsSize = [i["size"] for i in body["volumes"] if i["type"] == "EBS"]
            if len(ebsSize) > 0:
                buildParameters["EBSROOTVOLSIZE"] = str(ebsSize[0])
            fsxSize = [i["size"] for i in body["volumes"] if i["type"] == "FSX"]
            if len(fsxSize) > 0:
                buildParameters["fsxStorageCapacity"] = str(fsxSize[0])
        buildParameters["InstanceType"] = body["nodes"][0]["code"]
        return buildParameters
    except Exception as E:
        logger.warning("launchSingleNode-" + str(datetime.datetime.now()))
        logger.warning(E)
        raise  # re-raise so withoutCodeBuild surfaces the real message

def _get_db_port(engine):
    """Return default port number string for a given DB engine."""
    engine = (engine or "").lower()
    if "postgres" in engine:
        return "5432"
    if "oracle" in engine:
        return "1521"
    if "sqlserver" in engine:
        return "1433"
    if "redshift" in engine:
        return "5439"
    return "3306"  # mysql / mariadb default


def _get_db_status(cf_status):
    """Map a CloudFormation stack status to a Numen resource status string."""
    if "IN_PROGRESS" in cf_status:
        return "inprogress"
    if cf_status in ("CREATE_COMPLETE", "UPDATE_COMPLETE"):
        return "running"
    if "FAILED" in cf_status or cf_status == "ROLLBACK_COMPLETE":
        return "failed"
    if "DELETE" in cf_status:
        return "terminated"
    return "inprogress"


def _get_rds_actual_status(stack_name):
    """Query actual RDS instance status. Returns 'running', 'stopped', or 'inprogress'."""
    try:
        resp = cfnclient.describe_stack_resources(StackName=stack_name)
        db_id = next(
            (r["PhysicalResourceId"] for r in resp.get("StackResources", [])
             if r.get("ResourceType") == "AWS::RDS::DBInstance"),
            None
        )
        if not db_id:
            return "running"
        status = rdsClient.describe_db_instances(DBInstanceIdentifier=db_id
                    )["DBInstances"][0].get("DBInstanceStatus", "available")
        if status == "available":
            return "running"
        if status == "stopped":
            return "stopped"
        return "inprogress"
    except Exception as e:
        logger.warning(f"_get_rds_actual_status {stack_name}: {e}")
        return "running"


def _get_redshift_actual_status(stack_name):
    """Query actual Redshift cluster status. Returns 'running', 'stopped', or 'inprogress'."""
    try:
        resp = cfnclient.describe_stack_resources(StackName=stack_name)
        cluster_id = next(
            (r["PhysicalResourceId"] for r in resp.get("StackResources", [])
             if r.get("ResourceType") == "AWS::Redshift::Cluster"),
            None
        )
        if not cluster_id:
            return "running"
        status = redshiftClient.describe_clusters(ClusterIdentifier=cluster_id
                    )["Clusters"][0].get("ClusterStatus", "available")
        if status == "available":
            return "running"
        if status == "paused":
            return "stopped"
        return "inprogress"
    except Exception as e:
        logger.warning(f"_get_redshift_actual_status {stack_name}: {e}")
        return "running"


def _store_db_secret(stack_name, username, password, engine, dbname):
    """Store DB credentials in Secrets Manager keyed to the stack name."""
    secret_name = f"numen-dbcreds-{stack_name}"
    secret_value = json.dumps({
        "username": username,
        "password": password,
        "engine": engine,
        "dbname": dbname,
        "port": _get_db_port(engine),
    })
    try:
        secretsmanager_client.create_secret(
            Name=secret_name,
            SecretString=secret_value,
            Tags=[
                {"Key": "Platform",   "Value": "Numen"},
                {"Key": "StackName",  "Value": stack_name},
            ],
        )
    except secretsmanager_client.exceptions.ResourceExistsException:
        secretsmanager_client.put_secret_value(
            SecretId=secret_name,
            SecretString=secret_value,
        )
    except Exception as e:
        logger.warning(f"_store_db_secret failed for {stack_name}: {e}")


def generateDbPassword(length=16, engine="mysql"):
    """
    Generate a secure random password for the given DB engine.

    Each engine has its own restrictions on which special characters are allowed:
      Oracle        — only $, #, _ are permitted; & and most punctuation are banned.
                      Password must start with a letter (enforced by always placing a
                      letter first before the final shuffle).
      Redshift      — only $, #, _ are safe (same restrictions as Oracle).
      SQL Server    — most chars allowed but single-quote (') and double-quote (")
                      cause TSQL parsing issues; excluded here.
      MySQL/MariaDB — & is technically allowed but causes shell-expansion issues in
                      many client tools, so we exclude it.
      PostgreSQL    — similar caution; & excluded.
      default       — conservative safe set used for any unrecognised engine.
    """
    import secrets
    import string

    engine = (engine or "mysql").lower()

    if engine in ("oracle-ee", "oracle-se2", "oracle-se1", "oracle-se", "oracle"):
        # Oracle: alphanumeric + $, #, _ only; must start with a letter
        special  = "$#_"
        alphabet = string.ascii_letters + string.digits + special
        # First char must be a letter
        first    = secrets.choice(string.ascii_letters)
        rest = (
            secrets.choice(string.ascii_uppercase) +
            secrets.choice(string.ascii_lowercase) +
            secrets.choice(string.digits) +
            secrets.choice(special) +
            ''.join(secrets.choice(alphabet) for _ in range(max(0, length - 5)))
        )
        lst = list(rest)
        import random
        random.shuffle(lst)
        return first + ''.join(lst)

    elif "redshift" in engine:
        # Redshift: same safe set as Oracle
        special  = "$#_"
        alphabet = string.ascii_letters + string.digits + special

    elif "sqlserver" in engine:
        # SQL Server: exclude ' and " to avoid TSQL quoting issues
        special  = "!#$%*+-.=?@_"
        alphabet = string.ascii_letters + string.digits + special

    else:
        # MySQL, MariaDB, PostgreSQL, Aurora variants:
        # Exclude & (shell expansion), ', ", /, \, @, spaces
        special  = "!#$%*+-=?_"
        alphabet = string.ascii_letters + string.digits + special

    # Guarantee at least one of each required character class
    password = (
        secrets.choice(string.ascii_uppercase) +
        secrets.choice(string.ascii_lowercase) +
        secrets.choice(string.digits) +
        secrets.choice(special) +
        ''.join(secrets.choice(alphabet) for _ in range(max(0, length - 4)))
    )
    lst = list(password)
    import random
    random.shuffle(lst)
    return ''.join(lst)


def launchRDS(body):
    """
    Builds the CloudFormation parameter dictionary for an RDS instance launch.
    Uses values from body["databaseConfig"] merged with buildData["rds"] defaults.
    """
    # Map retired engine versions to their supported replacements.
    # Add entries here whenever AWS retires a minor version.
    _RETIRED_VERSIONS = {
        "mysql": {
            "8.0.28": "8.0.39",
            "8.0.32": "8.0.39",
            "8.0.33": "8.0.39",
            "8.0.34": "8.0.39",
            "5.7.44": "8.0.39",
            "5.7.43": "8.0.39",
        },
        "postgres": {
            "16.1": "16.4",
            "15.5": "15.8",
            "14.10": "14.13",
            "13.13": "13.16",
        },
        "aurora-mysql": {
            "8.0.mysql_aurora.3.04.0": "8.0.mysql_aurora.3.07.1",
            "5.7.mysql_aurora.2.11.3": "8.0.mysql_aurora.3.07.1",
        },
        "aurora-postgresql": {
            "15.4": "16.4",
            "14.9": "15.8",
            "13.12": "14.13",
        },
        "mariadb": {
            "10.11.6": "10.11.9",
            "10.6.16": "10.6.19",
            "10.5.23": "10.5.25",
        },
    }

    try:
        cfg = body.get("databaseConfig", {})
        defaults = dict(buildData.get("rds", {}))

        # Identify the DB identifier (max 63 chars, alphanumeric + hyphens)
        db_id = ("numen-rds-" + str(body["stackID"]))[:63]

        engine = cfg.get("engine", defaults.get("DBEngine", "mysql"))
        db_name = cfg.get("dbName", defaults.get("DBName", "numendatabase"))

        # Oracle: DBName is the SID — max 8 chars, alphanumeric only, uppercase
        if engine in ("oracle-ee", "oracle-se2", "oracle-se1", "oracle-se"):
            import re as _re
            db_name = _re.sub(r'[^A-Za-z0-9]', '', db_name)[:8].upper() or "ORCL"

        # SQL Server: DBName parameter not supported — omit it
        sqlserver_engines = ("sqlserver-se", "sqlserver-ee", "sqlserver-ex", "sqlserver-web")
        include_db_name = engine not in sqlserver_engines

        # Remap retired engine versions to their supported replacements
        requested_version = cfg.get("engineVersion", "")
        engine_version = _RETIRED_VERSIONS.get(engine, {}).get(requested_version, requested_version)
        if requested_version and requested_version != engine_version:
            logger.warning(f"launchRDS: retired version {requested_version} remapped to {engine_version}")

        parameters = {
            "DBInstanceIdentifier": db_id,
            "DBEngine":             engine,
            "DBEngineVersion":      engine_version,
            "DBInstanceClass":      cfg.get("dbInstanceClass", defaults.get("DBInstanceClass", "db.t3.medium")),
            "AllocatedStorage":     str(cfg.get("allocatedStorage", defaults.get("AllocatedStorage", "20"))),
            "MaxAllocatedStorage":  str(cfg.get("maxAllocatedStorage", defaults.get("MaxAllocatedStorage", "200"))),
            "MultiAZ":              str(cfg.get("multiAZ", False)).lower(),
            "StorageType":          cfg.get("storageType", defaults.get("StorageType", "gp3")),
            "MasterUsername":       defaults.get("MasterUsername", "admin"),
            "MasterUserPassword":   generateDbPassword(engine=engine),
            "BackupRetentionPeriod": str(cfg.get("backupRetentionPeriod", defaults.get("BackupRetentionPeriod", "7"))),
            "VpcId":                defaults.get("VpcId", configdata.get("vpcid", "")),
            "SubnetId1":            defaults.get("SubnetId1", configdata.get("mastersubnetid", "")),
            "SubnetId2":            defaults.get("SubnetId2", configdata.get("mastersubnetid", "")),
            "VpcSecurityGroupId":   defaults.get("VpcSecurityGroupId", configdata.get("additionalsecuritygroupid", "")),
            "CREATEDBY":            body.get("email", "numen-user"),
            "Environment":          configdata.get("environment", "dev"),
        }
        if include_db_name:
            parameters["DBName"] = db_name
        # Remove empty engineVersion to let CFN use the default
        if not parameters["DBEngineVersion"]:
            del parameters["DBEngineVersion"]
        return parameters
    except Exception as E:
        logger.warning("launchRDS-" + str(datetime.datetime.now()))
        logger.warning(E)
        return {}


def rdsBuild(parameters, stackName, createdBy="numen-user", user_tags=None):
    """Creates a CloudFormation stack for the RDS instance."""
    try:
        with open('staticfiles/assets/Json/ctx-numen-rds-template.yml', 'r') as f:
            template_body = f.read()
        parametersIns = [{'ParameterKey': k, 'ParameterValue': str(v)} for k, v in parameters.items()]
        tags = [
            {'Key': 'Platform', 'Value': 'Numen'},
            {'Key': 'CREATEDBY', 'Value': createdBy},
            {'Key': 'Environment', 'Value': configdata.get("environment", "dev")},
            {'Key': 'ResourceType', 'Value': 'RDS'},
        ]
        for ut in (user_tags or []):
            if ut.get("Key") and ut.get("Value"):
                tags.append({'Key': ut["Key"], 'Value': str(ut["Value"])})
        response = cfnclient.create_stack(
            StackName=stackName,
            TemplateBody=template_body,
            Parameters=parametersIns,
            Tags=tags,
        )
        # Store credentials in Secrets Manager for later retrieval
        _store_db_secret(
            stack_name=stackName,
            username=parameters.get("MasterUsername", "admin"),
            password=parameters.get("MasterUserPassword", ""),
            engine=parameters.get("DBEngine", "mysql"),
            dbname=parameters.get("DBName", ""),
        )
        return response
    except Exception as E:
        logger.warning("rdsBuild-" + str(datetime.datetime.now()))
        logger.warning(E)
        raise


def launchRedshift(body):
    """
    Builds the CloudFormation parameter dictionary for a Redshift cluster launch.
    Uses values from body["databaseConfig"] merged with buildData["redshift"] defaults.
    """
    try:
        cfg = body.get("databaseConfig", {})
        defaults = dict(buildData.get("redshift", {}))

        cluster_id = ("numen-rs-" + str(body["stackID"]))[:63]
        cluster_type = cfg.get("clusterType", defaults.get("ClusterType", "multi-node"))
        num_nodes = str(cfg.get("numberOfNodes", defaults.get("NumberOfNodes", "2")))

        parameters = {
            "ClusterIdentifier":                cluster_id,
            "NodeType":                         cfg.get("nodeType", defaults.get("NodeType", "dc2.large")),
            "ClusterType":                      cluster_type,
            "NumberOfNodes":                    num_nodes,
            "DBName":                           cfg.get("dbName", defaults.get("DBName", "numendw")),
            "MasterUsername":                   defaults.get("MasterUsername", "admin"),
            "MasterUserPassword":               generateDbPassword(length=20, engine="redshift"),
            "AutomatedSnapshotRetentionPeriod": str(defaults.get("AutomatedSnapshotRetentionPeriod", "7")),
            "VpcId":                            defaults.get("VpcId", configdata.get("vpcid", "")),
            "SubnetId1":                        defaults.get("SubnetId1", configdata.get("mastersubnetid", "")),
            "SubnetId2":                        defaults.get("SubnetId2", configdata.get("mastersubnetid", "")),
            "VpcSecurityGroupId":               defaults.get("VpcSecurityGroupId", configdata.get("additionalsecuritygroupid", "")),
            "CREATEDBY":                        body.get("email", "numen-user"),
            "Environment":                      configdata.get("environment", "dev"),
        }
        # single-node clusters don't take NumberOfNodes
        if cluster_type == "single-node":
            parameters["NumberOfNodes"] = "1"
        return parameters
    except Exception as E:
        logger.warning("launchRedshift-" + str(datetime.datetime.now()))
        logger.warning(E)
        return {}


def redshiftBuild(parameters, stackName, createdBy="numen-user", user_tags=None):
    """Creates a CloudFormation stack for the Redshift cluster."""
    try:
        with open('staticfiles/assets/Json/ctx-numen-redshift-template.yml', 'r') as f:
            template_body = f.read()
        parametersIns = [{'ParameterKey': k, 'ParameterValue': str(v)} for k, v in parameters.items()]
        tags = [
            {'Key': 'Platform', 'Value': 'Numen'},
            {'Key': 'CREATEDBY', 'Value': createdBy},
            {'Key': 'Environment', 'Value': configdata.get("environment", "dev")},
            {'Key': 'ResourceType', 'Value': 'Redshift'},
        ]
        for ut in (user_tags or []):
            if ut.get("Key") and ut.get("Value"):
                tags.append({'Key': ut["Key"], 'Value': str(ut["Value"])})
        response = cfnclient.create_stack(
            StackName=stackName,
            TemplateBody=template_body,
            Parameters=parametersIns,
            Tags=tags,
        )
        # Store credentials in Secrets Manager for later retrieval
        _store_db_secret(
            stack_name=stackName,
            username=parameters.get("MasterUsername", "admin"),
            password=parameters.get("MasterUserPassword", ""),
            engine="redshift",
            dbname=parameters.get("DBName", "numendw"),
        )
        return response
    except Exception as E:
        logger.warning("redshiftBuild-" + str(datetime.datetime.now()))
        logger.warning(E)
        raise


def launchSageMaker(body):
    """
    Builds the parameter dictionary for the SageMaker CFT.
    The notebook instance name (ResId) must be <=63 chars, alphanumeric + hyphens.
    """
    try:
        resId = "sm-" + body["stackName"]
        resId = resId[:63]  # SageMaker notebook name length limit
        parameters = {}
        parameters["InstanceType"]    = body["nodes"][0]["code"]
        parameters["ResId"]           = resId
        parameters["InstanceName"]    = configdata["instanceidprefix"] + str(body["stackID"])
        parameters["CreatedBy"]       = body["email"]
        parameters["Environment"]     = configdata["environment"]
        parameters["SubnetId"]        = configdata["subnetid"]
        parameters["SecurityGroupId"] = configdata["additionalsecuritygroupid"]
        parameters["IAMRoleName"]     = configdata.get("sagemakerexecutionrolename",
                                            buildData["sagemaker"]["IAMRoleName"])
        ebs_sizes = [i["size"] for i in body.get("volumes", []) if i["type"] == "EBS"]
        parameters["VolumeSizeInGB"]  = str(ebs_sizes[0]) if ebs_sizes else buildData["sagemaker"]["VolumeSizeInGB"]
        return parameters
    except Exception as E:
        logger.warning("launchSageMaker-" + str(datetime.datetime.now()))
        logger.warning(E)


def sageMakerBuild(parameters, stackName):
    """
    Creates a CloudFormation stack for the SageMaker Notebook Instance.
    """
    try:
        with open('staticfiles/assets/Json/ctx-numen-sagemaker-template.yml', 'r') as f:
            template_body = f.read()
        parametersIns = [
            {'ParameterKey': k, 'ParameterValue': str(v)}
            for k, v in parameters.items()
        ]
        tags = [
            {'Key': 'Platform',    'Value': 'Numen'},
            {'Key': 'CREATEDBY',   'Value': parameters["CreatedBy"]},
            {'Key': 'CUSTOMNAME',  'Value': parameters["ResId"]},
            {'Key': 'Environment', 'Value': parameters["Environment"]}
        ]
        response = cfnclient.create_stack(
            StackName=stackName,
            TemplateBody=template_body,
            Parameters=parametersIns,
            Tags=tags
        )
        return response
    except Exception as E:
        logger.warning("sageMakerBuild-" + str(datetime.datetime.now()))
        logger.warning(E)


@csrf_exempt
def getResourceDetails(request):
    """
    Returns connection details for an RDS, Redshift, or SageMaker resource.
    GET params: stackName, resourceType (RDS | REDSHIFT | SAGEMAKER)
    """
    try:
        stack_name   = request.GET.get("stackName", "").strip()
        resource_type = request.GET.get("resourceType", "").strip().upper()

        if not stack_name:
            return JsonResponse({"error": "stackName is required"}, status=400)

        # Fetch CloudFormation stack details
        try:
            cf_resp = cfnclient.describe_stacks(StackName=stack_name)
            stack   = cf_resp["Stacks"][0]
        except Exception as e:
            return JsonResponse({"error": f"Stack not found: {str(e)}"}, status=404)

        outputs      = {o["OutputKey"]: o["OutputValue"] for o in stack.get("Outputs", [])}
        cf_params    = {p["ParameterKey"]: p["ParameterValue"] for p in stack.get("Parameters", [])}
        stack_status = stack["StackStatus"]

        result = {
            "stackName":   stack_name,
            "stackStatus": stack_status,
            "region":      region_name,
            "resourceType": resource_type,
        }

        if resource_type == "RDS":
            endpoint = outputs.get("DBEndpoint", "")
            port     = outputs.get("DBPort", "3306")

            # Retrieve credentials from Secrets Manager
            try:
                secret_resp = secretsmanager_client.get_secret_value(SecretId=f"numen-dbcreds-{stack_name}")
                creds = json.loads(secret_resp["SecretString"])
            except Exception:
                creds = {}

            engine   = creds.get("engine",   cf_params.get("DBEngine", "mysql"))
            username = creds.get("username", "admin")
            password = creds.get("password", "N/A – secret not found")
            dbname   = creds.get("dbname",   cf_params.get("DBName", ""))

            # Build a ready-to-use connection string
            if "postgres" in engine:
                conn_str = f"psql -h {endpoint} -p {port} -U {username} -d {dbname}"
            elif "oracle" in engine:
                conn_str = f"sqlplus {username}@{endpoint}:{port}/{dbname}"
            elif "sqlserver" in engine:
                conn_str = f"sqlcmd -S {endpoint},{port} -U {username}"
            else:
                conn_str = f"mysql -h {endpoint} -P {port} -u {username} -p"

            result.update({
                "endpoint":         endpoint,
                "port":             port,
                "username":         username,
                "password":         password,
                "dbname":           dbname,
                "engine":           engine,
                "connectionString": conn_str,
            })

        elif resource_type == "REDSHIFT":
            endpoint = outputs.get("ClusterEndpoint", "")
            port     = outputs.get("ClusterPort", "5439")

            try:
                secret_resp = secretsmanager_client.get_secret_value(SecretId=f"numen-dbcreds-{stack_name}")
                creds = json.loads(secret_resp["SecretString"])
            except Exception:
                creds = {}

            username = creds.get("username", "admin")
            password = creds.get("password", "N/A – secret not found")
            dbname   = creds.get("dbname",   cf_params.get("DBName", "numendw"))

            conn_str = f"psql -h {endpoint} -p {port} -U {username} -d {dbname}"
            cluster_id = outputs.get("ClusterId", stack_name)
            query_editor_url = (
                f"https://{region_name}.console.aws.amazon.com/redshiftv2/home"
                f"?region={region_name}#query-editor-v2"
            )

            result.update({
                "endpoint":         endpoint,
                "port":             port,
                "username":         username,
                "password":         password,
                "dbname":           dbname,
                "connectionString": conn_str,
                "queryEditorUrl":   query_editor_url,
                "clusterId":        cluster_id,
            })

        elif resource_type == "SAGEMAKER":
            notebook_name = outputs.get("NumenSageMakerName", cf_params.get("ResId", ""))
            instance_type = cf_params.get("InstanceType", "")

            notebook_url = ""
            if notebook_name:
                try:
                    sm_resp      = sagemakerClient.create_presigned_notebook_instance_url(
                        NotebookInstanceName=notebook_name,
                        SessionExpirationDurationInSeconds=1800,
                    )
                    notebook_url = sm_resp["AuthorizedUrl"]
                except Exception as e:
                    logger.warning(f"SageMaker presigned URL failed: {e}")

            result.update({
                "notebookName": notebook_name,
                "notebookUrl":  notebook_url,
                "instanceType": instance_type,
            })

        else:
            return JsonResponse({"error": f"Unsupported resourceType: {resource_type}"}, status=400)

        return JsonResponse(result)

    except Exception as e:
        logger.warning(f"getResourceDetails-{datetime.datetime.now()}: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def getDatabaseResources(request):
    """
    Returns RDS, Redshift, and SageMaker CloudFormation stacks owned by the
    requesting user, formatted like result.json entries so the frontend can
    display them alongside EC2 resources.
    """
    try:
        username   = request.GET.get("username", "")
        sm_prefix  = configdata.get("smstackprefix", "SM-EC2-CURIA-")

        # Statuses we care about (exclude DELETE_COMPLETE)
        active_statuses = [
            "CREATE_IN_PROGRESS", "CREATE_COMPLETE", "CREATE_FAILED",
            "UPDATE_IN_PROGRESS", "UPDATE_COMPLETE", "UPDATE_ROLLBACK_COMPLETE",
            "ROLLBACK_IN_PROGRESS", "ROLLBACK_COMPLETE",
            "DELETE_IN_PROGRESS",
        ]

        db_resources = {
            "Inprogress": [],
            "Running":    [],
            "Stopped":    [],
            "Failed":     [],
            "Terminated": [],
        }

        paginator = cfnclient.get_paginator("list_stacks")
        for page in paginator.paginate(StackStatusFilter=active_statuses):
            for summary in page.get("StackSummaries", []):
                sname = summary["StackName"]

                # Identify resource type by stack name prefix
                if sname.startswith("numen-rds-"):
                    rt = "RDS"
                elif sname.startswith("numen-rs-"):
                    rt = "REDSHIFT"
                elif sname.startswith(sm_prefix):
                    rt = "SAGEMAKER"
                else:
                    continue

                # Fetch full stack to check CREATEDBY tag
                try:
                    detail = cfnclient.describe_stacks(StackName=sname)
                    stack  = detail["Stacks"][0]
                except Exception:
                    continue

                tags = {t["Key"]: t["Value"] for t in stack.get("Tags", [])}
                if tags.get("CREATEDBY") != username:
                    continue

                status_str  = stack["StackStatus"]
                numen_status = _get_db_status(status_str)

                # For CREATE_COMPLETE stacks, override with real AWS resource status
                if numen_status == "running":
                    if rt == "RDS":
                        numen_status = _get_rds_actual_status(sname)
                    elif rt == "REDSHIFT":
                        numen_status = _get_redshift_actual_status(sname)

                item = {
                    "StackId":      stack["StackId"],
                    "StackName":    sname,
                    "CreationTime": stack["CreationTime"].isoformat(),
                    "StackStatus":  status_str,
                    "DriftInformation": {"StackDriftStatus": "NOT_CHECKED"},
                    "displayName":  sname,
                    "instanceId":   sname,          # stack name used as identifier
                    "CREATEDBY":    username,
                    "sharable":     "false",
                    "sharedInstance": False,
                    "sharedBy":     None,
                    "appType":      "database",
                    "resourceType": rt,
                    "status":       numen_status,
                    "message":      stack.get("StackStatusReason", ""),
                    "instanceDetails": {
                        "Application Name": rt,
                        "nodeType":         "database",
                        "machineType":      rt,
                        "OS":               "",
                        "ebsSize":          "",
                        "fsxSize":          "",
                        "slurmqueues":      [],
                        "dataSources":      [],
                    },
                }

                if numen_status == "inprogress":
                    db_resources["Inprogress"].append(item)
                elif numen_status == "running":
                    db_resources["Running"].append(item)
                elif numen_status == "stopped":
                    db_resources["Stopped"].append(item)
                elif numen_status == "failed":
                    db_resources["Failed"].append(item)
                elif numen_status == "terminated":
                    db_resources["Terminated"].append(item)

        return JsonResponse({"data": db_resources, "userName": username})

    except Exception as e:
        logger.warning(f"getDatabaseResources-{datetime.datetime.now()}: {e}")
        return JsonResponse({"error": str(e)}, status=500)


def singleNodeBuild(parameters, os):
    try:
        if os != "windows":
            with open('staticfiles/assets/Json/ctx-numen-singlenode-template.yml', 'r') as f:
                template_body = f.read()
        else:
            with open('staticfiles/assets/Json/ctx-numen-singlenode-windows-template.yml', 'r') as f:
                template_body = f.read()
        response = cfnclient.create_stack(
            StackName=parameters["stackName"],
            TemplateBody=template_body,
            Parameters=parameters["envVariables"],
            Tags=parameters["InstanceTags"]
        )
        return response
    except Exception as E:
        logger.warning("singleNodeBuild-" + str(datetime.datetime.now()))
        logger.warning(E)
        raise  # re-raise so the caller can surface the real CloudFormation error


def launchParallelCluster(body):
    try:
        buildParameters= buildData["parallelCluster"].copy()  # copy to avoid mutating shared config dict
        Packages=body["applicationName"]
        os = body["os"]
        #buildParameters["CUSTOMAMI"] = getCustomAMI(Packages,body["os"])
        buildParameters["CUSTOMAMI"] = getCustomAMI(body["os"], packages=body.get("applicationName"))
        clusterName = body["stackName"]
        buildParameters["MASTERNODETYPE"] = body["nodes"][0]["code"]
        buildParameters["CLUSTERNAME"] = clusterName
        buildParameters["CUSTOMNAME"] = clusterName
        buildParameters["PACKAGES"] = Packages
        buildParameters["IDLETIME"] = str(body["idleTimeout"]["value"])
        buildParameters["ENVIRONMENT"] = configdata["environment"]
        slurmQueues = []
        for x,i in enumerate(body["nodeGroups"]):
            if i["code"].split('-')[0] == "cpu":
                instn = getInstances(i["code"])
            else:
                instn = getInstancesGPU(i["code"])
            slurmQueues.append(i["code"])
            buildParameters["PART"+str(x+1)+"_TYPE"]=instn
            buildParameters["PART"+str(x+1)+"_NAME"]=i["code"]
            buildParameters["PART"+str(x +1)+"_MAXCOUNT"]=str(i["count"])
        if len(body["volumes"]) > 0:
            ebsSize = [i["size"] for i in body["volumes"] if i["type"] == "EBS"]
            if(len(ebsSize)) > 0:
                buildParameters["MASTERROOTVOLSIZE"] = str(ebsSize[0])
                buildParameters["COMPUTEROOTVOLSIZE"] = str(ebsSize[0])
        buildParameters["BASEOS"] = body["os"]
        buildParameters["accountid"] = stsClient.get_caller_identity()["Account"]
        buildParameters["CREATEDBY"] = body["email"]
        buildParameters["SLURMQUEUES"] = ":".join(slurmQueues)
        buildParameters["INSTANCENAME"]=configdata["instanceidprefix"]+ str(body["stackID"])
        #buildParameters["ondemandFSXfsid"] = body["ondemandFSXfsid"]
        return buildParameters
    except Exception as E:
        logger.warning("launchParallelCluster-"+str(datetime.datetime.now()))
        logger.warning(E)
        raise  # re-raise so withoutCodeBuild's except can return a proper error response

def parallelNodeBuild(parameters,stackName):
    try:
        with open('staticfiles/assets/Json/pcluster.template.3.2.1.j2') as f:
            templatedata=f.read()
        template = Template(templatedata)
        print(parameters)
        config = template.render(env=parameters, name='pcluster')
        with open('staticfiles/assets/pClusterConfigs/'+parameters["CLUSTERNAME"]+'.config', 'w') as f:
            f.write(config)
        # Sync pcluster scripts to cluster-specific S3 prefix and WAIT for completion
        sync_result = subprocess.run(
            ["aws", "s3", "sync",
             "s3://"+configdata["resourcebucket"]+"/pcluster/",
             "s3://"+configdata["resourcebucket"]+"/parallelcluster-"+parameters["CLUSTERNAME"]+"/"],
            capture_output=True, text=True
        )
        if sync_result.returncode != 0:
            logger.warning("parallelNodeBuild-s3sync failed: " + sync_result.stderr)
        rc = runSubprocess(parameters,stackName)
        return rc
    except Exception as E:
        logger.warning("parallelNodeBuild-"+str(datetime.datetime.now()))
        logger.warning(E)
        raise  # re-raise so withoutCodeBuild's except can return a proper error response

def runSubprocess(parameters,stackName):

    try:
        # Merge stderr into stdout so we capture pcluster errors too
        process=subprocess.Popen(
            ["pcluster", "create-cluster",
             "-c", "staticfiles/assets/pClusterConfigs/"+parameters["CLUSTERNAME"]+".config",
             "-n", stackName,
             "--rollback-on-failure", "false"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        allOutput = []
        # Iterate over lines until EOF — no infinite loop
        for rawLine in process.stdout:
            output = rawLine.strip().decode(errors='replace')
            logger.warning(output)
            allOutput.append(output)
            if "cloudformationStackStatus" in output:
                try:
                    os.remove("staticfiles/assets/pClusterConfigs/"+parameters["CLUSTERNAME"]+".config")
                except Exception:
                    pass
                return output
        process.wait()
        # pcluster exited without printing cloudformationStackStatus — return whatever it printed
        fullOutput = " ".join(allOutput)
        logger.warning("runSubprocess-pcluster did not return cloudformationStackStatus. Full output: " + fullOutput)
        return fullOutput if fullOutput else "pcluster exited without status"
    except Exception as E:
        logger.warning("runSubprocess-"+str(datetime.datetime.now()))
        logger.warning(E)
        raise

def createFsxForInstance(parameters,fsxSize, stackname,stackID):
    try:
        if parameters["clusterType"] == "SINGLE":
            stackname = "sn-"+ stackname
        response = fsxClient.create_file_system(ClientRequestToken=str(uuid.uuid4()),FileSystemType='LUSTRE',StorageCapacity=fsxSize,SubnetIds=[configdata["mastersubnetid"]],SecurityGroupIds=[buildData["parallelCluster"]["ADDITIONALSECURITYGROUPID"]],Tags=[{'Key': 'Name', 'Value': configdata["fsxprefix"]},{'Key': 'FSXName', 'Value': stackname},{'Key': 'environment','Value':configdata["environment"]},{'Key': 'CREATEDBY','Value': parameters["email"]}],
        FileSystemTypeVersion="2.12",LustreConfiguration={'DataCompressionType': 'LZ4','DeploymentType': "PERSISTENT_2",'PerUnitStorageThroughput': 125})
        FileSystemId=response['FileSystem']['FileSystemId']
        ondemandfsxstatus = ""
        """ while [[ ondemandfsxstatus != 'AVAILABLE' ]]:
            ondemandfsxstatus = fsxClient.describe_file_systems(
                                FileSystemIds=[
                                    FileSystemId,
                                ],
                            )
            ondemandfsxstatus = ondemandfsxstatus["FileSystems"][0]['Lifecycle']
            print(ondemandfsxstatus)
            print("waiting for OndemandFSx to be available")
            time.sleep(30) """
        return FileSystemId
    except Exception as E:
        logger.warning("createFsxForInstance-"+str(datetime.datetime.now()))
        logger.warning(E)

def removeStackId(stackName):
    try:
        stackID = stackName.split("-")
        stackID = stackID[-1]
        stackID = "{:03d}".format(int(stackID))
        instanceData["instanceID"].remove(stackID)
        with open("staticfiles/assets/Json/instanceCount.json","w") as outfile:
            json.dump(instanceData, outfile,default=str)
    except Exception as E:
        logger.warning("createFsxForInstance-"+str(datetime.datetime.now()))
        logger.warning(E)


def list_s3_objects(request):
    prefix = request.GET.get('prefix', '') 
    if prefix and not prefix.endswith('/'):
        prefix += '/'
    try:
        paginator = s3Client.get_paginator('list_objects_v2')
        operation_params = {
            'Bucket': s3_projectsbucket_name,
            'Prefix': prefix,
            'Delimiter': '/'  # delimiter for folders
        }
        print("operation_params",operation_params)
        
        folders = []
        files = []

        page_iterator = paginator.paginate(**operation_params)
        for page in page_iterator:
            print("Each Page",page)
            for cp in page.get('CommonPrefixes', []):
                folder_name = cp.get('Prefix').rstrip('/').split('/')[-1]
                folders.append(folder_name)
            for obj in page.get('Contents', []):
                key = obj['Key']
                if key.endswith('/'):
                    continue
                file_name = key.split('/')[-1]
                files.append(file_name)
        
        return JsonResponse({'folders': folders, 'files': files})
    
    except Exception as e:
        logger.error(f"S3 list error: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt   
def create_s3_folder(request):
    try:
        data = json.loads(request.body)
        folder_name = data.get('folderName')
        if not folder_name:
            return JsonResponse({'error': 'Folder name is required'}, status=400)

        if not folder_name.endswith('/'):
            folder_name += '/'

        s3Client.put_object(Bucket=s3_projectsbucket_name, Key=folder_name)

        return JsonResponse({'message': f'Folder "{folder_name}" created successfully.'})
    except Exception as e:
        logger.error(f"Error creating folder: {e}")
        return JsonResponse({'error': str(e)}, status=500)


def get_download_url(request):
    try:
        key = request.GET.get('key')
        if not key:
            return JsonResponse({'error': 'Key parameter is required'}, status=400)

        url = s3Client.generate_presigned_url(
            'get_object',
            Params={'Bucket': s3_projectsbucket_name, 'Key': key, 'ResponseContentDisposition': 'attachment'},
            ExpiresIn=3600 
        )

        return JsonResponse({'url': url})
    except Exception as e:
        logger.error(f"Error generating download URL: {e}")
        return JsonResponse({'error': str(e)}, status=500)
    
@csrf_exempt
def generate_presigned_urls(request):
    """
    Request: { "files": ["file1.png", "file2.pdf"], "folder": "my-uploads/" }
    Response: { "urls": { "file1.png": "<url1>", "file2.pdf": "<url2>" } }
    """
    try:
        body = json.loads(request.body.decode("utf-8"))
        files = body.get("files", [])
        folder = body.get("folder", "")

        urls = {}
        for filename in files:
            key = f"{folder}{filename}" if folder else filename
            presigned_url = s3Client.generate_presigned_url(
                "put_object",
                Params={"Bucket": s3_projectsbucket_name, "Key": key},
                ExpiresIn=3600,  # 1 hour
            )
            urls[filename] = presigned_url

        return JsonResponse({"urls": urls})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# ── SSM Shell Terminal ────────────────────────────────────────────────────────
# Requires:
#   1. AWS CLI installed on this server  (`aws --version`)
#   2. Session Manager plugin installed  (`session-manager-plugin`)
#   3. IAM role with ssm:StartSession permission on target instances
#
# Active sessions are stored in-process.  They are cleaned up when the frontend
# calls /stopShell or when the underlying SSM process exits.
# ---------------------------------------------------------------------------

import threading
import select as _select

_shell_sessions: dict = {}   # sessionId -> { proc, master_fd, lock }


@csrf_exempt
def startShell(request):
    """
    POST { instanceId, stackName }
    Spawns `aws ssm start-session --target <instanceId>` inside a PTY.
    Returns { sessionId } so the frontend can poll for output.
    """
    try:
        import pty
        body = json.loads(request.body)
        instance_id = body.get("instanceId", "").strip()
        if not instance_id:
            return JsonResponse({"error": "instanceId required"}, status=400)

        master_fd, slave_fd = pty.openpty()

        proc = subprocess.Popen(
            ["aws", "ssm", "start-session", "--target", instance_id,
             "--region", region_name],
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            close_fds=True,
            preexec_fn=os.setsid,
        )
        os.close(slave_fd)

        session_id = str(uuid.uuid4())
        _shell_sessions[session_id] = {
            "proc":      proc,
            "master_fd": master_fd,
            "lock":      threading.Lock(),
        }

        logger.info(f"startShell: session {session_id} -> instance {instance_id}")
        return JsonResponse({"sessionId": session_id})

    except Exception as e:
        logger.warning(f"startShell error: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def shellInput(request):
    """
    POST { sessionId, data }
    Writes raw bytes (keystrokes) to the PTY master.
    """
    try:
        body = json.loads(request.body)
        session_id = body.get("sessionId", "")
        data       = body.get("data", "")

        session = _shell_sessions.get(session_id)
        if not session:
            return JsonResponse({"error": "session not found"}, status=404)

        with session["lock"]:
            os.write(session["master_fd"], data.encode("utf-8", errors="replace"))

        return JsonResponse({"ok": True})

    except OSError:
        # PTY closed
        return JsonResponse({"ok": False, "closed": True})
    except Exception as e:
        logger.warning(f"shellInput error: {e}")
        return JsonResponse({"error": str(e)}, status=500)


def shellOutput(request):
    """
    GET ?sessionId=<id>
    Reads whatever output is currently available from the PTY (non-blocking,
    up to 50 ms wait).  Returns { output: "<text>" }.
    """
    try:
        session_id = request.GET.get("sessionId", "")
        session    = _shell_sessions.get(session_id)

        if not session:
            return JsonResponse({"output": "", "closed": True})

        master_fd = session["master_fd"]
        output    = ""

        # Drain up to 4 KB with a 50 ms timeout so we never block the request
        try:
            ready, _, _ = _select.select([master_fd], [], [], 0.05)
            if ready:
                data   = os.read(master_fd, 4096)
                output = data.decode("utf-8", errors="replace")
        except OSError:
            # PTY has been closed (process exited)
            _shell_sessions.pop(session_id, None)
            return JsonResponse({"output": output, "closed": True})

        return JsonResponse({"output": output, "closed": False})

    except Exception as e:
        logger.warning(f"shellOutput error: {e}")
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def stopShell(request):
    """
    POST { sessionId }
    Terminates the SSM process and closes the PTY.
    """
    try:
        body       = json.loads(request.body)
        session_id = body.get("sessionId", "")
        session    = _shell_sessions.pop(session_id, None)

        if session:
            try:
                session["proc"].terminate()
            except Exception:
                pass
            try:
                os.close(session["master_fd"])
            except Exception:
                pass
            logger.info(f"stopShell: closed session {session_id}")

        return JsonResponse({"ok": True})

    except Exception as e:
        logger.warning(f"stopShell error: {e}")
        return JsonResponse({"error": str(e)}, status=500)
