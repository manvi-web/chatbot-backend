# Relion 3.1 User Guide

## SCOPE

The Relion 3.1 User guide tells you about the **Relion 3.1** Launch steps & processes involved in the NUMEN platform for deploying a Standalone and/or an HPC Cluster on AWS.

## AUDIENCE

1. Scientists
2. IT Admins

## Terminology

1. **Parallel Cluster** - AWS ParallelCluster is an open source cluster management tool that makes it easy for you to deploy and manage High Performance Computing (HPC) clusters on AWS.

2. **Standalone Instance/singlenode** - A single EC2 Instance.

3. **Instance Type** - Different resource combinations of CPUs, Memory, Storage etc

4. **FSx/FSx Lustre** - Fully managed shared storage built on the world's most popular high-performance file system Lustre.

5. **DCV** - NICE DCV is a high-performance remote display protocol that provides customers with a secure way to deliver remote desktops.

## INTRODUCTION

**RELION** is an image processing software designed specifically for Cryo-electron Microscopy (cryo-EM). It is a standalone computer program built for the refinement of macromolecular structures by single-particle analysis of electron cryo-microscopy data.
Relion employs an empirical Bayesian approach for the refinement of multiple 3D reconstructions or 2D class averages. With alternative approaches often relying on user expertise for the tuning of parameters, it can find an optimal way of filtering the data automatically.

In **NUMEN** platform, every application deployment will be done using a separate AMI containing Relion version 3.1 installed. Using the AMI containing Relion 3.1 already installed we can create standalone as well as cluster environments.

## Launching Relion 3.1 using NUMEN

1. Login to the Numen server UI.

   ![Relion3.1](../../static/assets/img/documentImages/Relion3.1.png)

2. Once logged in, you will be able to see the Scientific Computing application icons under the Applications section.

3. To select Relion 3.1, click on the Relion 3.1 icon.

   ![SelectRelion3.1](../../static/assets/img/documentImages/SelectRelion3.1.png)

4. Once you select the Relion 3.1 as an application, Ubuntu 2004 will get auto selected as a base OS.

   ![OSubuntu](../../static/assets/img/documentImages/OSubuntu.png)

5. By default single node will get selected once you select Relion 3.1.

   ![singlenode](../../static/assets/img/documentImages/singlenode.png)

6. If you want to launch the Relion 3.1 along with Paralell cluster, you need to select the parallel cluster from the 'Infrastructure section', instead of singlenode.

   ![pc](../../static/assets/img/documentImages/pc.png)

7. If you want to launch Relion 3.1 there are two options you have, 'Express launch' and 'Custom Launch'.

8. If you select 'Express launch' It will ask for your confirmation to proceed.

9. Once confirmed, it will directly launch Relion 3.1 server with some prebuild configurations.

10. Another Option is 'Custom Launch' where you will see more options to customise your application installation.

11. Once you clicked on 'Custom launch', it will give you a landing page with two different options 'Recommended' & Customise.

    ![recommended](../../static/assets/img/documentImages/recommended.png)

<!-- 12. When you select Recommended you will find 3 recommended infrastructure configurations, with default recommended configurations for 'Single node' as well as 'Parallel Cluster'. -->

<!-- 13. If you click on the 'instance', you will get recommended instance type by default for standalone instance and other recommended settings like FSx, EBS, etc according to your selected infrastructure configuration i.e., small, medium or large. And If you click on 'Parallel Cluster' you can see recommended Master Node, Compute Node Instance Types, No of Compute Nodes and other settings like FSx, EBS, IDLETIME, etc according to your category of selection i.e., small, medium or large.
 -->
12. Another Option is 'Customise', here you can choose and customise the infrastructure as per your need.

    ![Customised](../../static/assets/img/documentImages/Customised.png)

13. You can customise your selection, you can choose to launch either a single node or a Parallel Cluster from the Clustering section, and you can choose the instance type that you want to use as per your use case, for Master Node when you select Parallel Cluster in Clustering section and for a Standalone instance and Compute Nodes (in case you selected Parallel Cluster option) you can choose from Instances Section, Also, a pop-up will be appeared to select a number of compute nodes you want to configure once you select the instance type (in case you selected Parallel Cluster option). Along with this, you are allowed to choose Filesystems from the FileSystem section. You can also find the estimated cost right side of your selections.

14. You can also apply the Idle termination on your selected resources for 30 minutes, 60 minutes, and 90 minutes.

15. Once you are done with your configuration selections, click on Launch and you will be asked for confirmation, once confirmed Relion 3.1 application will get launched.

16. Once the application is launched you can track the progress under 'Display Resources', which you will find in the 'Right side corner top, on the NUMEN Ui.

17. Once the resources are provisioned, you need to click on the 'link' sign and you will get a DCV link, from where you can access the Relion 3.1 Environment you just created.

18. We will suggest you select 'Custom Launch' and it will give you the landing page from where you can choose the infrastructure configuration as per your requirements

19. Also, FSx will get auto-mounted on the Relion 3.1 server and you will be able to access it under '/fsx/', containing Relion 3.1 reference data.

## RECOMMENDED PROCEDURE

1. The following is what we typically do for each new data set for which we have a decent initial model.

2. If you don't have an initial model: perform RCT, tomography+sub-tomogram averaging, or common-lines/stochastic procedures in a different program.

### Getting Organized

1. Save all your micrographs in one or more subdirectories of the project directory (from where you'll launch the RELION GUI).
2. For some reason if you don't want to place your micrographs inside the RELION project directory, then inside the project directory you can also make a symbolic link to the directory where your micrographs are stored.
3. If you for some reason do not want to place your micrographs inside the RELION project directory, then inside the project directory you can also make a symbolic link to the directory where your micrographs are stored.
4. If you have recorded any movies (e.g. from your direct-electron detector), then store each movie next to a single-frame micrograph that is the average of that movie.
5. You will do your CTF estimation, particle picking, and initial refinements and classifications using the average micrograph, and only use the actual movies in the later stages.
6. The naming convention is very important: strictly called the average micrograph with whatever name you like, but with a. mrc extension (e.g. mic001.mrc), and then call your movie with the same name; PLUS and underscore; PLUS a movie-identifier that you always keep the same; PLUS a .mrcs extension (e.g. mic001_movie.mrcs).

### Particle selection & pre-processing

1. You typically should start by estimating the CTFs for all micrographs from the corresponding Tab in the GUI.
2. Be careful at this stage: you are probably better at getting rid of bad/junk particles than any of the classification procedures below! So spend a decent amount of time on selecting good particles, be it manually or (semi-)automatically.
3. Also from version 1.3, RELION implements reference-based automated particle picking.
4. Typically, one first manually picks a subset of the available micrographs to obtain several hundreds to a few thousand particles.
5. With these particles, one then performs an initial 2D classification run.
6. From the resulting class averages one selects the best and most representative views to be used as references in the autopicking program.
7. Note that the reference-based auto-picking will work best when the class averages are on the same intensity-scale as the signal in your data: therefore, it's best to generate the references from the data themselves, or at least from a similar data set. E.g. do not use negative-stain class averages to pick a cryo-EM data set: this will not work very well.
8. For a 4kx4k micrograph and say ~10 references, the auto-picking will take approximately half an hour per micrograph.
9. There are two parameters to be optimised: a threshold (higher value means fewer, better particles) and a minimum inter-particle distance.
10. Because re-running half-an-hour calculations for every trial of these parameters would be too time-consuming, you may write out intermediate figure-of-merit (FOM) maps for each reference.
11. After these have been written out, one can re-calculate new coordinate files in several seconds with different threshold and inter-particle distance parameters.
12. However, because the FOM maps are many large files, one cannot run the autopicking program in parallel when writing out FOM maps (it could bring your file system down). Therefore, it is recommended to:

    ```
    1. Write the FOM maps only for a few (good and bad) micrographs in an initial, sequential run.
    2. Re-read those FOM maps in subsequent (very fast) runs to find the best threshold and inter-particle distance for those micrographs.
    3. Delete the FOM maps.
    4. Run the autopicking in parallel for all micrographs using the optimised parameters (but without reading/writing FOM maps).
    ```

13. After picking the particles, you should extract, normalize, and invert contrast (if necessary to get white particles) the particles.
14. If you experience any type of problem with RELION when using particles that were extracted (and/or pre-processed) by another program, then first try using the entire CTF estimation and particle extraction procedures through the RELION GUI.
15. Re-doing your preprocessing inside RELION is very fast (it's fully parallelized); it is the most convenient way to prepare the correct STAR input files for you; and it prepares the images as is best for RELION.

### 2D class averaging

1. You would like to Calculate 2D class averages to get rid of bad/junk particles in the data set.
2. Apart from choosing a suitable particle diameter the most important parameters are the number of classes (K) and the regularization parameter T.
3. For cryo-EM we typically have at least 100-200 particles per class, so with 3,000 particles we would not use more than K=30 classes.
4. Also, to limit computational costs, we rarely use more than say 250 classes even for large data sets.
5. We typically do not touch the default sampling parameters, perhaps except for large icosahedral viruses where we sometimes use finer angular samplings.
6. Depending on how clean our data is, we some times repeat the process of 2D-class averaging to select good particles 2 or 3 times.
7. Having a clean data set is an important factor in getting good 3D reconstructions.

### 3D classification

1. Once we're happy with our data cleaning in 2D, we almost always Classify 3D structural heterogeneity.
2. if it is not reconstructed from the same data set in RELION or XMIPP, it is probably NOT on the correct grey scale.
3. Also, if it is not reconstructed with CTF correction in RELION or made from a PDB file, then one should probably also set "Has reference been CTF corrected?" to No.
4. We prefer to start from relatively harsh initial low-pass filters (often 40-60 Angstrom), and typically perform 25 iterations with a regularization factor T=4 for cryo-EM and T=2-4 for negative stain.
5. After classification, we select particles for each structural state of interest.

### 3D refinement

1. Each of the 3D classes of interest may be refined separately using the 3D-auto-refine procedure.
2. We often use the refined map of the corresponding class as the initial model and we start refinement again from a rather harsh initial low-pass filter, often 40-60 Angstroms.
3. We typically do not touch the default sampling parameters, except for icosahedral viruses where we may start from 3.7 degrees angular sampling, and we perform local searches from 0.9 degrees onwards.
4. After 3D refinement, we sharpen the map and calculate solvent-mask corrected resolution estimates using 'Post-processing'.
5. You will probably like this map and resolution estimate much better than the one that comes straight out of the refinement.

<!-- ## Relion Predownloaded Dataset and Download Scripts -

1. NUMEN provides pre-downloaded datasets for Relion, which is accessible under the /fsx/ directory.
2. " /fsx/datasets/ " contains two different types of datasets, one is for 'Beta_Galactosidase' and the other is for 'Plasmodium_Ribosome'.
3. If any user wants to re-download the datasets for 'Beta_Galactosedase', so he can use the shell script named -'download_betagalactosidase_dataset.sh' to download the same.
4. There are some pre-calculated results for Relion under 'PrecalculatedResults/'.
5. Similarly if someone wants to download the 'Plasmodium' dataset so it can easily get downloaded using the 'download_plasmodium_dataset.sh' script, which can be found under the 'Plasmodium_Ribosome/'. Directory -->

## Datasets
1. NUMEN provides data relevant to the both the CROs , which is accessible under the ``/data``, directory.
2. Users can create their own projects with respect to their needs and store the relevant data under ``/projects``.

© Clovertex, Inc. 2023, All rights reserved.

