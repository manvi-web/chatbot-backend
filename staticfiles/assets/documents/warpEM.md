# Warpem User Guide

## SCOPE

This Document talks about the **Warpem** deployment steps & processes involved in terms of NUMEN platform.

## INTRODUCTION

**Warpem** is an advanced real-time cryo-EM data pre-processing tool. that automates all preprocessing steps
 of cryo-EM data acquisition and enables real-time evaluation. Warp corrects micrographs for global and local
 motion, estimates the local defocus and monitors key parameters for each recorded micrograph or tomographic
 tilt series in real time. The software further includes deep-learning-based models for accurate particle
 picking and image denoising. The output from Warp can be fed into established programs for particle
 classification and 3D-map refinement.

**M** is a stand-alone program shipped with Warp. While Warp handles the first stages of the data processing
pipeline, M lives on its opposite end. It allows you to take refinement results from tools like RELION and perform a
multi-particle refinement.

## SOP

1. Login to the Numen server UI.
2. Once logged in , you will be able to see the Scientific Computing application icons under the Applications section.
3. In order to select Warpem, click on the warpem icon.

   ![Warpem](../../static/assets/img/documentImages/Warpem.png)
4. Once you select Warpem as an application, Windows will get auto selected as the base OS.

   ![OS](../../static/assets/img/documentImages/windows.png)

5. By default single node will get selected, once you select the Warpem.

   ![SingleNode](../../static/assets/img/documentImages/singlenode.png)

6. If you want to launch Warpem there are two launch options , 'Express launch' and 'Custom Launch'.

   ![Launchopt](../../static/assets/img/documentImages/Launchopt.png)

7. If you select 'Express launch' It will ask your confirmation to proceed.
8. Once confirmed, it will directly launch Warpem server with prebuilt configurations.
9. Other Option is 'Custom Launch' where you will get the more options to customise your application Launch.
10. Under Custom Launch Options, you can customise your selections, where you can choose from InstanceType, per your workload needs. Along with this you are allowed to choose EBS Filesystems Size etc.
11. For Warpem Application, by default with Express Launch the Server gets launched with g5.4xlarge as Instance Type.
12. On a Launched and built Warpem Application Server you would find the FSX Openzfs autimatically mounted.
13. Once you are done with your configuration selections, click on Launch and you will be asked for confirmation, once confirmed Warpem application will get launched.
14. Once application is launched you can track the progress under 'Display Resources' option, which could be found at the 'Top-right corner on the NUMEN Ui.

    ![displayResourcess](../../static/assets/img/documentImages/displayResourcess.png)
15. Once the launched resource is being provisioned, you need to click on the 'link' symbol and you will get a DCV link, from where you can access the Warpem Environment you just created.

    ![dcvlink](../../static/assets/img/documentImages/warpemdcvlink.png)
16. We will Suggest you to select the 'CUSTOM LAUNCH' and select the Instance type as per requirements.
17. Select the Custom launch, and it will give you the landing page from where you can choose the instance types suitung your workload.
18. Once you access the Warpem server with dcv, to access the openzfs storage the Network locations should be accessed as below. The Warpem applications would be available on the local Desktop as represented below.
   ![AppStorage](../../static/assets/img/documentImages/App_ozfs.png)


## Warpem TEST DATASET (Sample Test Job Run)
Warpem has been tested with some pre-downloaded datsets which is available on below given links.

## DOWNLOADING THE DATA

Please click on the below link to navigate to and download the data.

[Download Data From Here](https://www.ebi.ac.uk/empiar/EMPIAR-10153/#:~:text=Uncompressed%20ZIP%20archive-,streamed,-via%20HTTP)


