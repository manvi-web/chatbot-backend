# SBGrid User Guide

## SCOPE

This Document describes the **SBGrid** deployment procedures and steps as per the NUMEN platform.

## INTRODUCTION

**SBGrid** is the Structural Biology Grid software suite.

SBGrid is a global consortium of research labs in academia and industry using structural biology (cryoEM, X-ray crystallography and scattering, NMR, molecular dynamics, etc) to address scientific questions.

SBGrid focuses on building new tools to offer the user more efficient and customized software installation options, with a new Capsule environment that wraps all application dependencies and variables together for a faster and more reliable workflow, and a software installation client for all Linux and Mac users that allows the end user the flexibility to manage which software titles to install and when to kick off updates.

## SOP

1. Login to the NUMEN server UI.
2. Once logged in , you will be able to see the Scientific Computing application icons under the Applications section.
3. In order to select SBGrid, click on the SBGrid icon.

   ![SBGrid](../../static/assets/img/documentImages/SBGrid.png)

4. Once you selected the SBGrid as an application, Ubuntu will get auto selected as a base OS.

   ![OS](../../static/assets/img/documentImages/OS.png)

5. By default single node will get selected, once you select the SBGrid.

   ![SingleNode](../../static/assets/img/documentImages/SingleNode.png)

6. If you want to launch the SBGrid along with Parallel Cluster, you need to select the Parallel Cluster from the 'Infrastructure section', instead of Single Node.

   ![PC](../../static/assets/img/documentImages/pc.png)

7. By default three datasource will get integrated with SBgrid applications, as CryoEM projects, Home and CryoEm Data.

   ![DataSets](../../static/assets/img/documentImages/DataSets.png)

8. If you want to launch the SBGrid there are two option, 'Express launch' and 'Custom Launch'.

   ![Launchopt](../../static/assets/img/documentImages/Launchopt.png)

9. If you select 'Express launch' It will ask your confirmation to proceed.

10. Once confirm, it will launch SBGrid server with prebuild configurations.

11. Other option is 'Custom Launch' where you will get more options to customise your application installation.

12. You can customise your selections, across Clustering, where you can choose either single node you want to go with or Clustering, also you can choose instance type which you want to use as per your use cases, Along with this you are allowed to choose Filesystems, and environmental behaviour as Auto scaling and some other options.

    ![custom](../../static/assets/img/documentImages/custom.png)

13. On the Custom Launch landing page, you will get options for two different catogries of Machines (Instances), Either CPU or GPU, which you can choose as per your usecases.

    ![custom](../../static/assets/img/documentImages/custom.png)

14. You can also apply the Idle termination on your selected resourcess for 30 minutes, 60 minutes and 90 minutes.

15. Once the selection has been done you can click on the 'Launch' option, and a pop up window will ask for confirmation. Once confirmed the resource will start to get created.

    ![Launch](../../static/assets/img/documentImages/Launch.png)

16. Once you are done with your configuration selections, click on Launch and you will be asked for confirmation, once confirmed SBGrid application will get launched.

17. Once application is launched you can track the progress under 'Display Resources', which you will find on the 'Right side corner top, on the NUMEN Ui.

    ![displayResourcess](../../static/assets/img/documentImages/displayResourcess.png)

18. Once the resourcess are provisioned, you need to click on the 'link' symbol and you will get a DCV link, from where you can access the SBGrid Environment you just created.

    ![dcvlink](../../static/assets/img/documentImages/dcvlink.png)

19. We will Suggest you to select the 'CUSTOM LAUNCH' and select the Instance type as per requirements.

20. Select the Custom launch, and it will give you the landing page from where you can choose the instance types as per requirements, also choose the FSX which will get auto maounted on the SBGrid server master node and you will be able to access it under '/fsx/'.

21. Already downloaded data for SBGrid can bee seen under /fsx/, which is located in S3 and can be accessed via FSX lustre.
