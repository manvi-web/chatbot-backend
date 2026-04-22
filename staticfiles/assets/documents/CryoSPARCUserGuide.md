# CryoSPARC User Guide

## SCOPE

The CryoSPARC User guide tells you about the **CryoSPARC** Launch steps & processes involved in the NUMEN platform for deploying a Standalone and/or an HPC Cluster on AWS.

## AUDIENCE

1. Scientists
2. IT Admins

## Terminology

1. **Parallel Cluster** - AWS ParallelCluster is an open source cluster management tool that makes it easy for you to deploy and manage High Performance Computing (HPC) clusters on AWS.

2. **Standalone Instance/singlenode** - A single EC2 Instance.

3. **Instance Type** - Different resource combinations of CPUs, Memory, Storage etc

4. **FSx/FSx Lustre** - Fully managed shared storage built on the world's most popular high-performance file system Lustre.

5. **DCV** - NICE DCV is a high-performance remote display protocol that provides customers with a secure way to deliver remote desktop.

## INTRODUCTION

**CryoSPARC** (Cryo-EM Single Particle Ab-Initio Reconstruction and Classification) is a state-of-the-art software solution for the complete processing of single-particle cryo-electron microscopy (cryo-EM) data. CryoSPARC is useful for solving cryo-EM structures of membrane proteins, viruses, complexes, flexible molecules, small particles, phase plate data and negative stain data.

In **NUMEN** platform, every application deployment will be done using a separate AMI containing CryoSPARC installed. Using the AMI containing CryoSPARC already installed we can create standalone as well as cluster environments.

## Launching CryoSPARC using NUMEN

1. Login to the Numen server UI

   ![login](../../static/assets/img/documentImages/login.png)

2. Once logged in, you will be able to see the Scientific Computing application icons under the Applications section.

3. In order to select CryoSPARC, click on the CryoSPARC icon.

   ![Cryosparc](../../static/assets/img/documentImages/Cryosparc.png)

4. Once you select CryoSPARC as an application, alinux2 will get auto-selected as a base OS.

   ![OS](../../static/assets/img/documentImages/cryoali.png)

5. By default single node will get selected once you select the CryoSPARC.
6. If you want to launch the CryoSPARC along with Paralell cluster, you need to select the parallel cluster from the 'Infrastructure section', instead of singlenode.

   ![PC](../../static/assets/img/documentImages/pc.png)

7. If you want to launch the CryoSPARC there are two options you have, 'Express launch' and 'Custom Launch'.

   ![options](../../static/assets/img/documentImages/LaunchOptions.png)

8. If you select 'Express launch' It will ask your confirmation to proceed.

9. Once confirm, it will directly launch CryoSPARC server with some prebuild configurations.

10. Other Option is 'Custom Launch' where you will get more options to customise your application installation.

   <!--  ![customLaunch](../../static/assets/img/documentImages/CustomLaunch.png) -->

11. You can customise your selection, you can choose to launch either a single node or a Parallel Cluster from the Clustering section, and you can choose the instance type that you want to use as per your use case, for Master Node when you select Parallel Cluster in Clustering section and for a Standalone instance and Compute Nodes (in case you selected Parallel Cluster option) you can choose from Instances Section, Also, a pop-up will be appeared to select a number of compute nodes you want to configure once you select the instance type (in case you selected Parallel Cluster option). Along with this, you are allowed to choose Filesystems from FileSystem section. You can also find the estimated cost right side of your selections.

    ![estimate](../../static/assets/img/documentImages/estimate.png)

12. You can also apply the Idle termination on your selected resources for 30 minutes, 60 minutes, and 90 minutes.

<!-- 13. When you get the landing page for 'CustomLaunch' you will find 3 recommended infrastructure configurations, with default recommended configurations for 'Single node' as well as 'Parallel Cluster'.

14. If you click on the 'instance', you will get recommended instance type by default for standalone instance and other recommended settings like FSx, EBS, etc according to your selected infrastructure configuration i.e., small, medium, or large. And if you click on 'Parallel Cluster' you can see recommended Master Node, Compute Node Instance Types, No of Compute Nodes and other settings like FSx, EBS, IDLETIME, etc according to your category of selection i.e., small, medium or large. -->

    ![recomendation](../../static/assets/img/documentImages/recomendation.png)

13. Once you are done with your configuration selections, click on Launch and you will be asked for confirmation, once confirmed CryoSPARC application will get launched.

14. Once the application is launched you can track the progress under 'Display Resources', which you will find on the 'Right side corner top, on the NUMEN Ui.

    ![displatResources](../../static/assets/img/documentImages/displatResources.png)

15. Once the resources are provisioned, you need to click on the 'link' sign and you will get a DCV link, from where you can access the CryoSPARC Environment you just created.

16. We will suggest you select 'CUSTOM LAUNCH' and it will give you the landing page from where you can choose the infrastructure configuration as per your requirements

17. Also, FSx which will get auto-mounted on the server and you will be able to access it under '/fsx/'.
