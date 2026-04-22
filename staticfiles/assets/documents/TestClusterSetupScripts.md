# Test Cluster Setup Scripts 

## SCOPE
This Document talks about the steps & processes involved in the deployment of the ‘Parallel Cluster’, using code pipeline repositories, unique to each person. 

## INTRODUCTION: 
This repo and associated pipeline will be deploying the code commits and related pipelines for Parallel cluster deployment. Using email addresses will create separate and unique clusters for different users. 

 AWS (Amazon Web Services) Parallel Cluster is an AWS supported open-source cluster management tool that helps to deploy and manage high performance computing (HPC) clusters in the AWS Cloud. 

 ## SOP: 
 Below are the steps we need to follow to deploy the parallel cluster in the customer environment – 
 create a cloud9 environment at customer account for initial deployment and customization efforts. - we can use cloud shell instead of cloud 9 in the customer environment 

1. Create a cloud9 environment at customer account for initial deployment and customization efforts. - we can use cloud shell instead of cloud 9 in the customer environment 
2. download the files to cloud9/cloud shell from S3. 

3. unzip the encrypted package. 

4. Make necessary changes to the respective ‘scripts. -- not required  

5. Initially make changes to ‘ctx-hpc-test-fsxl-generate-config.sh’ file such as, setting up the config file name, under the CONFIG parameter, setting up the ‘Tag’ values with respect to the customer environment, etc. 

6. Update the ‘ctx-hpc-driver-sync-config.sh’ file, with ‘config.json’ file. 

7. This will synchronize the changes updated in config.json file, to the S3 bucket" 

8. Update the config.j2’ file with environment variables according to the customer’s environment, 

       eg: "ctxenvironment=dev" 

9. Use ‘ctx-hpc-test-fsxl-generate-config.sh’ to update the configurations, which will be under /home/ec2-user/environment/ctx-hpc-driver/scripts/. 
10.  It will get the variable names from the jinja [ctx-hpc-config-test.j2] file.
11. Secondly it will start configuration of config parameters by customizing config file with account specific information. 
12.  Next stage is for Creating security groups.
13.  This step will also deploy the additional security groups using cloud formation stack [/home/ec2-user/environment/ctx-hpc-driver/scripts/deploy-cft.sh ctx-hpc-fsxlustre-sg-dev--deploy]. 
14.  Next step will be for the deployment of parallel cluster followed by CryoSPARC deployment.
15.  Once we run the bash script ‘ctx-hpc-test-fsxl-deploy.sh’, it will start calling another bashscripts sequentially, which will deploy the parallel cluster first and then the CryoSPARC application.  
16.  When we run “ctx-hpc-test-fsxl-deploy.sh”, it will check for ‘AWS -CLI’. 
17.  Once Aws cli is found, it will get the static variable names from Jinja file. 
18.   Later, will Customize config file with account specific information.
19.   Similarly, it will fetch the created resource details, such as - 
Lustre Security Group ID, EFS Security Group ID, EFS ID, etc.
20.   In the next stage, same script will try to grab the “keypair” details from   the ‘AWS Secret Manager’. 
21.   Also, it will get the SNS Topic for notifications. 
22.   Now ‘run_imagebuilder_pipeline_get_ami.sh’, script will Initiate an image builder run to create the image. 
23.    In lateral stage it will try to get AMI arn for alinux2. 
24.   Updates will happen in the Jinja template and generates a new config file, by configuring config Params. 
25.   Once the configuration is done, all the environment variables will get sourced, as mentioned. 
26.   Once the sourcing is finished, Syncing will happen from the local config file to the S3 bucket. 
27.   It will upload to s3 [ctx-hpc-config-bench.json to <s3://ctx-hpc-bench-fsxl/ctx-hpc-config-fsxl.json>].
28.   Now the flow will start deploying ctx-hpc-parallelcluster-pipeline stack, using ‘ctx-hpc-parallelcluster-pipeline.yml’.
29.   ctx-hpc-parallelcluster-pipeline-fsxl-deploy , is deployed now. 
   
