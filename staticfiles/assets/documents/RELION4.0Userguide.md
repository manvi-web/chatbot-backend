# Relion 4.0 User Guide

## INTRODUCTION

**RELION** is an image processing software designed specifically for Cryo-electron Microscopy (cryo-EM). It is a stand-alone computer program built for the refinement of macromolecular structures by single-particle analysis of electron cryo-microscopy data.
Relion employs an empirical Bayesian approach for refinement of multiple 3D reconstructions or 2D class averages. With alternative approaches often relying on user expertise for the tuning of parameters, it can find an optimal way of filtering the data automatically.

In **NUMEN** platform as per the Clovertex Standard Practice, every application deployment will be done through the code pipeline only. We have created a seperate imagebuilder pipline which will create the AMI containing Relion application already installed. Using this AMI, we can create the standalone as well as paralell cluster environments.

## SOP

1. Login to the Numen server UI.

   ![Relion 4.0](../../static/assets/img/documentImages/Relion4.0.png)

2. Once logged in , you will be able to see the Scientific Computing application icons under the Applications section.
3. In order to select Relion 4.0, click on the Relion 4.0 icon.

   ![SelectRelion 4.0](../../static/assets/img/documentImages/SelectRelionVersion4.0.png)

4. Once you select the Relion 4.0 as an application, Alinux2 will get auto selected as a base OS.

   ![OSubuntu](../../static/assets/img/documentImages/relion4WithDefaultAlinux2.png)

5. By default single node will get selected, once you select the Relion 4.0.

   ![singlenode](../../static/assets/img/documentImages/singlenode.png)

6. If you want to launch the Relion 4.0 along with Paralell cluster, you need to select the parallel cluster from the 'Infrastructure section', instead of singlenode.

   ![pc](../../static/assets/img/documentImages/pc.png)

7. If you want to launch the Relion 4.0 there are two options you have, 'Express launch' and 'Custom Launch'.
8. If you select 'Express launch' It will ask your confirmation to proceed.
9. Once confirm, it will directly launch Relion 4.0 server with some prebuild configurations.
10. Other Option is 'Custom Launch' where you will get the more options to customise your application installation.
11. You can customise your selections accross Clustering, where you can chose either single node you want to go with or Clustering.
12. Also you can chose instance type which you want to use as per your use cases.
13. You can also apply the Idle termination on your selected resourcess for 30 minutes, 60 minutes and 90 minutes.
14. Once you clicked on 'Custom launch', it will give you a landing page with two different options as 'Recommended' & Customise.

    ![recommended](../../static/assets/img/documentImages/recommended.png)

15. Here you will get different multiple default suggestestions which will let you choose the resources, which are recommended with respect to the applications need and mechanism of working.
16. Other Option is 'Customise', here you can choose and customise the infrastructure as per your need.

    ![Customised](../../static/assets/img/documentImages/Customised.png)

17. Once you are done with your configuration selections, click on Launch and you will be asked for confirmation, once confirmed Relion 4.0 application will get launched.
18. Once application is launched you can track the progress under 'Display Resources', which you will find on the 'Right side corner top, on the NUMEN Ui.
19. Once the resourcess are provisioned, you need to click on the 'link' sign and you will get a DCV link, from where you can access the Relion 4.0 Environment you just created.
20. We will Suggest you to select the 'CUSTOM LAUNCH' and select the resources as per requirements.
21. Select the Custom launch, and it will give you the landing page from where you can choose the instance types as per requirements, also choose the FSX-4TB which will get auto mounted on the Relion 4.0 server and you will be able to access it under '/fsx/', containig Relion 4.0 reference data.

## RECOMMENDED PROCEDURE

1. The following is what we typically do for each new data set for which we have a decent initial model.
2. If you don't have an initial model: perform RCT, tomography+sub-tomogram averaging, or common-lines/stochastic procedures in a different program.

### Getting Organized

1.  Save all your micrographs in one or more subdirectories of the project directory (from where you'll launch the RELION GUI).
2.  For some reeason if you don't want to place your micrographs inside the RELION project directory, then inside the project directory you can also make a symbolic link to the directory where your micrographs are stored.
3.  If you for some reason do not want to place your micrographs inside the RELION project directory, then inside the project directory you can also make a symbolic link to the directory where your micrographs are stored.
4.  If you have recorded any movies (e.g. from your direct-electron detector), then store each movie next to a single-frame micrograph that is the average of that movie.
5.  You will do your CTF estimation, particle picking and initial refinements and classifications using the average micrograph, and only use the actual movies in the later stages.
6.  The naming convention is very important: strictly called the average micrograph with whatever name you like, but with a .mrc extension (e.g. mic001.mrc), and then call you movie with the same name; PLUS and underscore; PLUS a movie-identifier that you always keep the same; PLUS a .mrcs extension (e.g. mic001_movie.mrcs).

### Particle selection & preprocessing

1. You typically should start by estimating the CTFs for all micrographs from the corresponding Tab in the GUI.
2. Be careful at this stage: you are probably better at getting rid of bad/junk particles than any of the classification procedures below! So spend a decent amount of time on selecting good particles, be it manually or (semi-)automatically.
3. Also from version 1.3, RELION implements reference-based automated particle picking.
4. Typically, one first manually picks a subset of the available micrographs to obtain several hundreds to a few thousand particles.
5. With these particles, one then performs an initial 2D classification run.
6. From the resulting class averages one selects the best and most representative views to be used as references in the autopicking program.
7. Note that the reference-based auto-picking will work best when the class averages are on the same intensity-scale as the signal in your data: therefore it's best to generate the references from the data themselves, or at least from a similar data set. E.g. do not use negative-stain class averages to pick a cryo-EM data set: this will not work very well.
8. For a 4kx4k micrograph and say ~10 references, the auto-picking will take approximately half an hour per micrograph.
9. There are two parameters to be optimised: a threshold (higher value means fewer, better particles) and a minimum inter-particle distance.
10. Because re-running half-an-hour calculations for every trial of these parameters would be too time-consuming, you may write out intermediate figure-of-merit (FOM) maps for each reference.
11. After these have been written out, one can re-calculate new coordinate files in several seconds with different threshold and inter-particle distance parameters.
12. However, because the FOM maps are many large files, one cannot run the autopicking program in parallel when writing out FOM maps (it could bring your file system down).Therefore, it is recommended to:

    ```
    1. Write the FOM maps only for a few (good and bad) micrographs in an initial, sequential run.
    2. Re-read those FOM maps in subsequent (very fast) runs to find the best threshold and inter-particle distance for those micrographs.
    3. Delete the FOM maps.
    4. Run the autopicking in parallel for all micrographs using the optimised parameters (but without reading/writing FOM maps).
    ```

13. After picking the particles, you should extract, normalize and invert contrast (if necessary to get white particles) the particles.
14. If you experience any type of problem with RELION when using particles that were extracted (and/or preprocessed) by another program, then first try using the entire CTF estimation and particle extraction procedures through the RELION GUI.
15. Re-doing your preprocesing inside RELION is very fast (it's fully parallelized); it is the most convenient way to prepare the correct STAR input files for you; and it prepares the images as is best for RELION.

### 2D class averaging

1. You would like to Calculate 2D class averages to get rid of bad/junk particles in the data set.
2. Apart from choosing a suitable particle diameter the most important parameters are the number of classes (K) and the regularization parameter T.
3. For cryo-EM we typically have at least 100-200 particles per class, so with 3,000 particles we would not use more than K=30 classes.
4. Also, to limit computational costs, we rarely use more than say 250 classes even for large data sets.
5. We typically do not touch the default sampling parameters, perhaps with the exception of large icosahedral viruses where we sometimes use finer angular samplings.
6. Depending on how clean our data is, we some times repeat the process of 2D-class averaging to select good particles 2 or 3 times.
7. Having a clean data set is an important factor in getting good 3D reconstructions.

### 3D classification

1. Once we're happy with our data cleaning in 2D, we almost always Classify 3D structural heterogeneity.
2. if it is not reconstructed from the same data set in RELION or XMIPP, it is probably NOT on the correct grey scale.
3. Also, if it is not reconstructed with CTF correction in RELION or it is not made from a PDB file, then one should probably also set "Has reference been CTF corrected?" to No.
4. We prefer to start from relatively harsh initial low-pass filters (often 40-60 Angstrom), and typically perform 25 iterations with a regularization factor T=4 for cryo-EM and T=2-4 for negative stain.
5. After classification, we select particles for each structural state of interest.

### 3D refinement

1. Each of the 3D classes of interest may be refined separately using the 3D-auto-refine procedure.
2. We often use the refined map of the corresponding class as the initial model and we start refinement again from a rather harsh initial low-pass filter, often 40-60 Angstroms.
3. We typically do not touch the default sampling parameters, except for icosahedral viruses where we may start from 3.7 degrees angular sampling and we perform local searches from 0.9 degrees onwards.
4. After 3D refinement, we sharpen the map and calculate solvent-mask corrected resolution estimates using 'Post-processing'.
5. You will probably like this map and resolution estimate much better than the one that comes straight out of the refinement.

## Relion Predownloaded Dataset and Download Scripts

1. NUMEN provides, predownloaded datsets for Relion, which is accessible under the /fsx/ directory.
2. " /fsx/datasets/ " contains two different types of datasets, one is for 'Beta_Galactosidase' and the other is for 'Plasmodium_Ribosome'.
3. If any user wants to re-download the datasets for 'Beta_Galactosedase', so he can use the shell script named -'download_betagalactosidase_dataset.sh' to download the same.
4. There are some pre-calculated results for Relion under 'PrecalculatedResults/'.
5. Similarly if someone wants to download 'Plasmodium' dataset so it can easily get downloaded using 'download_plasmodium_dataset.sh' script, which can be found under the 'Plasmodium_Ribosome/' Directory.

## Best Practices / Recommendations

Please find some guidelines, recommendations, and best practices for Relion.
These settings will be just a starting point and depending on the datasets and problem at hand, the values may need to be adjusted significantly than what is recommended here.

### On GPU Enabled Steps -

1. Set “Number of MPI procs” to (Total Number of GPUs) + 1
2. Set “Number of Threads” to [3-9]
3. Set “WorkloadType” to gpu
4. Set “gres” to “gpu:<Max#ofGPUs/Instance>”
5. Set “Number of Nodes” to >1 to spread the workload across multiple nodes.
6. In Compute tab,
   - set “Use GPU acceleration?” to Yes
   - set “Which GPUs to use” to BLANK – remove the values.

### On CPU Enabled Steps -

1. On CPU compute nodes: [1]
2. Set “Number of MPI procs” to (Max number of CPUs per instance) – 1

3. Set “Number of Threads” to [1]

4. Set “WorkloadType” to cpu

5. Set “gres” to “gpu:0”

6. Set “Number of Nodes” to >1 to spread the workload across multiple nodes.

### In Compute tab -

1. Set “Copy particles to scratch directory” to /scratch//$SLURM_JOB_ID
2. Set “Pre-read all particles into RAM?” to No
3. Set “Number of pooled particles” to [3-100] with reverse correlation with MPI.

### Set “Memory” to higher or lower depending on the job size / steps.

## Relion Running Parameters Details

In this Section we will discuss running Relion jobs in an interactive environment through Relion GUI.

We would also see how we can bring variations to the job execution environment by changing the scheduler parameter through Relion GUI.

Once the required parameter for the job category has been applied, we will now move to the Running tab where we would enter/update the required resources to run the job. Those values will update from /etc/profile.d/relionsetguienv.sh

![reliongui](../../static/assets/img/documentImages/reliongui.png)

### As we see in the Running tab here, Following is the description about some of the parameters listed there:

1.  number of MPI Procs – The total number of Processes to be used to achieve faster execution using parallelism.

2.  number of threads – Threads allocated per process to achieve faster execution using parallelism.

3.  submit to queue – This should always be set to yes, as this avoids local submission of jobs to Head Node and schedules the job to a compute node.

4.  queue name – A unique name given to queue which houses compute machines with similar processing resources and characteristics. To know all the features please refer Section 2.HPC Queue and Instance Types. In order to let the scheduler, decide the queue for you, please leave the queue name as it is. Once you fill in all the scheduler-parameters your job will automatically be submitted to the compute queue containing that configuration.

5.  queue submit command – This should be set to sbatch as slurm directive to perform batch job execution.

6.  WorkloadType – Enter cpu or gpu depending on the compute-node type you want to run your jobs on.

7.  gres – This represents the scheduler directive for number of gpu per compute node required to run the job. For gpu workload type you should set minimum value as gpu:1. For cpu Workload type this must be set to gpu:0. Please see the ? Icon for more description on values for respective workload type.

8.  Memory - The memory in GB Per compute node, that is required to run the job. Please see the ? Icon for more description on maximum limit on values for respective workload type.

9.  NumberOfNodes – If we need to run multi-node job then we would use this field. This would make sure you obtain the desired number of compute nodes to run your job.

10. standard submission script – In the backend, we map the user selections set to a scheduler-specific script that finally maps to a batch script. This parameter points to that script.

After completing the parameters – we would click on Run! and see that a new job has been submitted to the scheduler, which completes the job execution.

`Please Note`: For Information on the number of GPU devices or the number of cores or Memory in GB or other details specific to the compute types, please refer to the HPC Queue, Instance Types, and Detail section before. The information provided in that section would be the driver to fill in the values for the fields in the Running tab.
