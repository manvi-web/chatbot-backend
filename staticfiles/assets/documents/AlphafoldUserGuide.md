# AlphaFold User Guide

## SCOPE

This Document talks about the AlphaFold deployment steps & processes involved in the NUMEN platform for deploying a Standalone and/or an HPC Cluster on AWS.

## AUDIENCE

1. Scientists
2. IT Admins

## Terminology

1. **Parallel Cluster** - AWS ParallelCluster is an open source cluster management tool that makes it easy for you to deploy and manage High Performance Computing (HPC) clusters on AWS.

2. **Standalone Instance/singlenode** – A single EC2 Instance.

3. **Instance Type** – Different resource combinations of CPUs, Memory, Storage etc

4. **FSx/FSx Lustre** - Fully managed shared storage built on the world's most popular high-performance file system Lustre.

5. **DCV** – NICE DCV is a high-performance remote display protocol that provides customers with a secure way to deliver remote desktops

## INTRODUCTION

AlphaFold is an artificial intelligence (AI) program that predicts the protein structure.

AlphaFold DB provides open access to over 200 million protein structure predictions to accelerate scientific research. In 2020, AlphaFold was recognized as a solution to the protein folding problem by the organizers of the CASP14 benchmark, a biennial challenge for research groups to test the accuracy of their predictions against real experimental data. In NUMEN platform, every application deployment will be done using a separate AMI containing AlphaFold version 2 installed using conda environment. Using the AMI containing AlphaFold already installed we can create standalone as well as cluster environments.

## LAUNCHING AlphaFold Using NUMEN

1. Login to the Numen server UI.

   ![Alphafold2](../../static/assets/img/documentImages/Alphafold2.png)

2. Once logged in, you will be able to see the Scientific Computing application icons under the Applications section.

3. To select AlphaFold, click on the AlphaFold icon.

   ![Alphafold](../../static/assets/img/documentImages/Alphafold.png)

4. Once you select the AlphaFold as an application, alinux2 will get auto-selected as a base OS.

   ![OS](../../static/assets/img/documentImages/OS.png)

5. By default single node will get selected once you select the AlphaFold.

6. If you want to launch the AlphaFold along with Parallel cluster, you need to select the parallel cluster from the 'Infrastructure section', instead of singlenode.

   ![PC](../../static/assets/img/documentImages/pc.png)

7. If you want to launch the AlphaFold there are two options you have, 'Express launch' and 'Custom Launch'.

   ![LaunchOptions](../../static/assets/img/documentImages/LaunchOptions.png)

8. If you select 'Express launch' It will ask for your confirmation to proceed.

9. Once confirmed, it will directly launch AlphaFold server with some prebuild configurations.

10. Another Option is 'Custom Launch' where you will get more options to customise your application installation.

11. You can customise your selection, you can choose to launch either a single node or a Parallel Cluster from the Clustering section, and you can choose the instance type that you want to use as per your use case, for Master Node when you select Parallel Cluster in Clustering section and for a Standalone instance and Compute Nodes (in case you selected Parallel Cluster option) you can choose from Instances Section, Also, a pop-up will be appeared to select a number of compute nodes you want to configure once you select the instance type (in case you selected Parallel Cluster option). Along with this, you are allowed to choose Filesystems from FileSystem section. You can also find the estimated cost right side of your selections.

    ![CustomLaunchSelectionTab](../../static/assets/img/documentImages/CustomLaunchSelectionTab.png)

12. You can also apply the Idle termination on your selected resources for 30 minutes, 60 minutes, and 90 minutes.

13. When you get the landing page for 'CustomLaunch' you will find 3 recommended infrastructure configurations, with default recommended configurations for 'Single node' as well as 'Parallel Cluster'.

14. If you click on the 'instance', you will get recommended instance type by default for standalone instance and other recommended settings like FSx, EBS, etc according to your selected infrastructure configuration i.e., small, medium, or large. And if you click on 'Parallel Cluster' you can see recommended Master Node, Compute Node Instance Types, No of Compute Nodes and other settings like FSx, EBS, IDLETIME, etc according to your category of selection i.e., small, medium or large.

    ![CustomOptions](../../static/assets/img/documentImages/CustomOptions.png)

15. Once you are done with your configuration selections, click on Launch and you will be asked for confirmation, once confirmed AlphaFold application will get launched.

16. Once the application is launched you can track the progress under 'Display Resources', which you will find in the 'Right side corner top, on the NUMEN Ui.

    ![DisplayResources](../../static/assets/img/documentImages/DisplayResources.png)

17. Once the resources are provisioned, you need to click on the 'link' sign and you will get a DCV link, from where you can access the AlphaFold Environment you just created.

18. We will suggest you select 'CUSTOM LAUNCH' and it will give you the landing page from where you can choose the infrastructure configuration as per your requirements

19. Also FSx lustre will get auto mounted on the Alphafold server and you will be able to access it under '/fsx/', containing alphafold reference data and sample scripts.

20. Reference data for Alphafold2 can be seen under /fsx/alphafold, which is in S3 and can be accessed via FSX luster.

## REFERENCE DATA

AlphaFold needs multiple genetic (sequence) databases to run as below -

        UniRef90,
        MGnify,
        BFD,
        Uniclust30,
        PDB70,
        PDB (structures in the mmCIF format)

In NUMEN, we already have stored these datasets under a S3 bucket, having size of ~ 2.2 TB.
These reference datasets are available on the Alphafold Server under the '/fsx/alphafold/' directory.

## INPUT FILE [SEQUENCE INPUT FILE]

For predicting the structure of certain protein sequences, we need to provide the sequence as an input file.
Input sequence for which you wish to predict the structure should be in FASTA file format, with the extension of '.fas', for example, 'A5A605.fas'.
It is recommended to keep the input sequence file along with the datasets.

## TEST SCRIPT

To run the Alphafold, NUMEN provides a prebuilt Test script, which will help you to predict the protein structure. You can find this script available on Alphafold server under the path '/fsx/alphafold_data/alphafold/run_alphafold.sh', with the name 'run_alphafold.sh'.

### How to Run the Script?

    bash run_alphafold.sh -d </path/to/dataDirectory> -o .</path/to/Output/directory/filename> -f </path/to/input/sequence/file.fas> -t <tag/you/want/example[2022-11-09]>

Example -

        #  For GPU -

    bash run_alphafold.sh -d /fsx/alphafold_data/af_download_data -o ./results/AMI-test-01/ -f /fsx/alphafold_data/af_download_data/A5A605.fas -t 2022-11-09

        # For CPU only -

    bash run_alphafold.sh -d /fsx/alphafoldv2/af_download_data -o ./dummy_test/ -f /fsx/alphafoldv2/af_download_data/P0A8I3.fas -t 2022-10-21 -g False

## ALPHAFOLD OUTPUT

The outputs will be stored in the directory you have mentioned while running the Alphafold, they include the computed MSAs, unrelaxed structures, relaxed structures, ranked structures, raw model outputs, prediction metadata, and section timings.

## BENCHMARKING AND RESULTS

Alphafold has been benchmarked for some of the Instance types, in order to get the fastest results.
Below are the glimpse of it along with results, which would help you to choose the appropriate resources -

- Processing is both Compute and I/O intensive.
- Process speeds up with more number of vCPUs [threads].
- I/O  intensive because, it uses input sequence to match with the most proximal protein structure in huge database, for prediction.
- Location of database also has an impact of query running time.

| Instance     | Instance Type | Run Type            | Run Time           |
| ------------ | ------------- | ------------------- | ------------------ |
| g4dn.4xlarge | GPU           | FSxL - non-hydrated | 2 hr 47 min 13 sec |
| g4dn.4xlarge | GPU           | FSxL - hydrated     | 3 hr 36 min 54 sec |
| G5.8xlarge   | GPU           | FSxL - non-hydrated | 1 hr 43 min 21 sec |
| G5.8xlarge   | GPU           | FSxL - hydrated     | 1 hr 17 min 07 sec |
| R6i.4xlarge  | CPU           | FSxL - non-hydrated | 3 hr 42 min 39 sec |
| R6i.8xlarge  | CPU           | FSxL - hydrated     | 1 hr 37 min 27 sec |
| Z1d.3xlarge  | CPU           | FSxL - non-hydrated | 3 hr 52 min 21 sec |


© Clovertex, Inc. 2023, All rights reserved 
