# User Guide

## SCOPE:

This document is about NUMEN platform version 1.0. This document also describes features and How to use the NUMEN platform. This document also contains a brief account on the process of parallel cluster deployments and flow of the resource creation during the Scientific Computing application deployments such as CryoSPARC, Relion, Gromacs and Alphafoldv2 using NUMEN.

## WHAT IS NUMEN?

NUMEN is an Application as Service Cloud Platform.
The application which enables the users to experience the Amazon Web Services in the most efficient way,
additionally it provides the users with an interactive UI.

## HOW TO CONNECT WITH NUMEN UI:

After the deployment of NUMEN application in your cloud environment, a working ALB link will be shared with you via Email, Once you click on that link you will get redirected to NUMEN UI.
Once the server is accessible, you will be landing on a login page. Use the credentials which are shared with you via email to login.

## FEATURES:

- Inbuilt integrated Scientific Computing applications as – Relion 3.x, CryoSPARC and Relion 4.0.
- Click based selection of Infrastructure components as OS, Packages, Data source and Servers or Clusters.
- One Go – deployment of Cluster or Stand-Alone servers for respective application.
- Visual Interface for Infrastructure Configuration.
- Display of Cost estimation as we select the resources or AWS services.
- Idle resource auto termination.

## FLOW OF WORKING:

-     As the NUMEN web ui, provides an automated, click based Infrastructure deployment feature, all we need to do is, to select the infrastructure components as per the requirement.
- The web ui contains the icons with respect to the infrastructure type such as Applications, Visualization tools, Packages, Operating Systems, Data Sources, and Infrastructure.

        Applications:       Relion 3.x, CryoSPARC, Relion 4.0,
                            Alphafold2, Gromacs
        Visualization:      Chimera, Phoenix, ChimeraX
        Packages:           R, Rstudio
        OS:		          Ubuntu 20.04, RedHat, Ubuntu, Centos, Alinux2
        Data Sources:       Sparc, Home, FSx, CrEMD
        Infrastructure:     Instance, paralellCluster,AWS-Batch,

  ![ConsoleViewNUMEN](../../static/assets/img/documentImages/userguide/ConsoleViewNUMEN.png)

- Below to the Features icons table, there are three functional Buttons, as – Clear, Express Launch & Custom Launch.

      Clear:
      This button will unselest or clear all the selected resources.
      Express Launch:
      This button makes the default resourcess to get launched and starts to build the respective environment.
      Custom Launch:
      This feature allows user to select and customize the enivironment by choosing the infrastructure components as per their requirements.

- While customizing the infrastructure using Custom Launch, users are having privilege to select either the single node mode of environment or the cluster mode.
- When a user selects single node user can select only one instance type and only one machine.
- When a user selects a cluster mode user can selects a maximum of five instances or five machines at a time.
- Once user selects any Instance type, it will ask the user how many cores he wants to go with or which instance type user wants to select.

  ![Buttons](../../static/assets/img/documentImages/userguide/Buttons.png)

-     This ‘NUMEN’ console is called as ‘Express launch’ because as soon as user selects an application by clicking on it, the console will also select other components as per the ‘preselect’ which is already built in by default.

        Eg : If user clicks  on ‘Relion4’ application, other infra components will get auto select by default like which OS, which machine, mode of environment as standalone or cluster, etc.

  ![DefaultSelections](../../static/assets/img/documentImages/userguide/DefaultSelections.png)

- If the default selection is not as per the requirements, users are having privilege to change the selections, and can opt for the other options.
-     Once the selection is done with respect to the requirements of the user, users need to click on the ‘Express Launch’ button.

  ![ExpressLaunch](../../static/assets/img/documentImages/userguide/ExpressLaunch.png)

-     Once you have launched the selection, on the right side up corner, you can track the process of deployment, you need to click on the ‘Application Console’ then ‘Display Resources’, and you can track the progress of the resources.

  ![DisplayResourcess](../../static/assets/img/documentImages/userguide/DisplayResourcess.png)

- As of now CryoSPARC works on only Parallel cluster, but Relion 3.x and relion 4.0 both works on single node as well as parallel cluster (With current release only).

- Numen ui also has a feature to provide the cost management by 'Idle termination' process.
  By default if a resource (instance/cluster) remains idle for 20 minutes, it will get auto terminated.
  20 minutes is a default value, but user can customize it to 30, 60 or 90 minutes as per the requirements.

- What ever resources user has created or what all environmental stacks are users running, they can monitor using the same NUMEN ui.

© Clovertex, Inc. 2023, All rights reserved.
