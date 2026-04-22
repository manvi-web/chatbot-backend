# Installation Guide

## Copyright by Clovertex Group LLC ###
This code repository contains confidential and proprietary content of Clovertex Group LLC 
If you have received it in error, please notify the sender immediately and then delete it 
Any unauthorized copying, disclosure, or distribution of this repository in whole or partially is strictly prohibited.

## SCOPE
This Document talks about the steps & processes involved in the deployment of the 'Numen' platform, using code pipeline repositories.

## OVERVIEW
NUMEN is an Application as a Service on AWS cloud Platform, which enables the Users/Scientists to experience the Amazon Web Services in a very simple and efficient way. Additionally it provides the users with an interactive UI, for the deployment and management of different Scientific Computing Applications such as Relion, cryoSPARC, GROMACS, and others, by providing multiple environment solutions.

## WHO CAN USE THIS GUIDE ?
The Administrators and Engineers who are responsible for the deployment of the 'Numen' platform into the client's AWS account.

## PREREQUISITES

###    CREATE AN APPLICATION INTEGRATION FROM THE RESPECTIVE IDENTITY PROVIDER (example - OKTA)
Navigate to the OKTA admin dashboard URL: *https://dev-86027508-admin.okta.com/admin/dashboard*

Under **Applications** tab click on Applications and Select **Create App Integration**.

Select **OIDC - OpenID Connect** when prompted for **Sign-in method** appears.

For **Application Type** click on **Web Application** Radio Button.

Click Next.

Now - We would need to fill the information for General Settings under the **New Web App Integration** Section

Provide suitable name for **App integration** name.

Select Check Box for **Authorization Code** contained in the **Grant type**
Finally - in the Assignments Section Under Controlled access Select Limit access to selected groups.
 for General Settings in APPLICATION.


Finally - in the **Assignments** Section Under **Controlled access** Select **Limit access to selected groups**.

Select the group from the drop down menu found in **Selected group(s)**, to confine the application access to desired group.
Click on Save.

**PLEASE NOTE** : Once Numen application deployment completes we would need to revisit this to update the LOGIN section of the application.
with Application Load Balancer URI's ,as noted in below steps.

1. Before Running the deployment steps below, please obtain the sso idp application's parameters mentioned as below - 
  
        client id
        clientsecret id
        issuer endpoint
        Authorization endpoint
        Token endpoint
        userinfo endpoint

2. The parameter clientid and clientsecret needs to be added as aws secrets Manager parameter with following attributes -
   
        Encryption key: aws/secretsmanager
        Secret name: ctx-numen-idp-sso
        Secret key: idpclientid, Secret value: xxxxxxxxxxxxxx
        Secret key: idpclientsecret, Secret value: yyyyyyyyyyyy

   

## DEPLOYMENT STEPS
### Step 1. Packaging Numen Application for Release and moving to Client environment
on HPC Numen Cloud9 , Run ./ctx-numen-package.sh to generate signed url.
Copy the last line at the end of the execution e.g. "curl .. ".
e.g. 

**curl -o ctx-numen-fullstack-XYZ.zip "https://ctx-hpc-driver-distribution.s3.us-e......**

SSO into the DEMO or CUSTOMER aws environment and make sure you are on the right region e.g. US-EAST-1

Create a CloudShell

Past the signed url copied to download the password-protected package file.

unzip [ package file downloaded ]

e.g. **ctx-numen-fullstack-XYZ.zip** from the above example


cd /home/cloudshell-user/home/ec2-user/environment/ctx-numen-fullstack

### Step 2. Modify the jinja Config File

**'Config.j2.numen'** is the file where we need to update the parameters according to the client's AWS account relevant different parameters.

### Step 3. Run 'deploy.sh' file
Once the parameters are all set, run command  'deploy.sh numen'.


### Step 4. Sourcing environment from the config.json file
**Deploy.sh** Script itself will take care to generate the 'config' file using a python script.
Once the 'Config' file is generated, it eventually gets sourced into the s3 resource bucket.

### Step 5. Creating 'resource bucket' if not exists
'deploy.sh' will now check for the 'resource bucket' in s3, if it exists it will upload the config file into it, if not exists, will create a new one with required configurations.
It's important to enable the versioning in the resource bucket, as 'Parallel Cluster' expects s3 bucket versioning enabled.

### Step 6. Creating 'dataset bucket' if not exists
'deploy.Sh' will now check for the 'dataset bucket' in the respective account, to create if not existing already.


### Step 7. Templatize Webapp ami Images File
For Several Numen Applications, Deployment expects prebuilt-ami's information into the config file.


### Step 8. Deploy Manage Prefix Lists
'deploy.sh' will create a managed prefix list.

### Step 9. Creating and Updating the config file
Once, we fetch the all required details, we are going to update the config file, into the resource bucket.


### Step 10. Sourcing environment from the configuration json file
All environment variables stored into the configuration file gets sourced into the source bucket.

### Step 11. Upload Certs for AWS Application Load Balancer
To check encryption certificates, if it already exists, will do nothing. If not, will create and upload to the Application LoadBalancer using upload_server_certs.sh script.

### Step 12. Manage generated Keypair with AWS Secrets Manager
Aws Secrets Manager is referenced for the generated keypairs, Skips generation if already present.

### Step 13. webapp stack  Deployment
Finally 'deploy.sh' script will invoke 'deploy_webapp_stack.sh' to deploy the Numen application into the configured region, using the config file from the resource bucket.

### Step 14.  Add login/redirect URI of the ALB into the idp
Once the webapp stack  deployment completes, a new ALB URL gets created corresponding to which the deployment directs the deployer to add/update redirect URI;s into IDP Application Integration.

### Step 15. Numen Application URL
The Deployment displays the Numen Application URL if the deployment is successful.

### Step 16. User Validation
Upon Reaching the Numen URL, Please Validate yourself through your corporate login credentials to access the Application.
