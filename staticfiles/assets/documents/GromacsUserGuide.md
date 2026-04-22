# GROMACS User Guide

## SCOPE

This Document talks about the **GROMACS** deployment steps & processes involved in terms of NUMEN platform.

## INTRODUCTION

**GROMACS** is a molecular dynamics package mainly designed for simulations of proteins, lipids and nucleic acids.
GROMACS is a versatile package to perform molecular dynamics, i.e. simulate the Newtonian equations of motion for systems with hundreds to millions of particles.

## SOP

1. Login to the Numen server UI.
2. Once logged in , you will be able to see the Scientific Computing application icons under the Applications section.
3. In order to select GROMACS, click on the GROMACS icon.

   ![Gromacs](../../static/assets/img/documentImages/Gromacs.png)

4. Once you selected the GROMACS as an application, alinux2 will get auto selected as a base OS.

   ![OS](../../static/assets/img/documentImages/alinux2.png)

5. By default single node will get selected, once you select the GROMACS.

   ![SingleNode](../../static/assets/img/documentImages/singlenode.png)

6. If you want to launch the GROMACS along with Paralell cluster, you need to select the parallel cluster from the 'Infrastructure section', instead of singlenode.

   ![PC](../../static/assets/img/documentImages/pc.png)

7. If you want to launch the GROMACS there are two options you have, 'Express launch' and 'Custom Launch'.

   ![Launchopt](../../static/assets/img/documentImages/Launchopt.png)

8. If you select 'Express launch' It will ask your confirmation to proceed.
9. Once confirm, it will directly launch GROMACS server with some prebuild configurations.
10. Other Option is 'Custom Launch' where you will get the more options to customise your application installation.
11. You can customise your selections, accross Clustering, where you can chose either single node you want to go with or Clustering, also you can chose instance type which you want to use as per your use cases, Along with this you are allowed to choose Filesystems, and environmental behavioura as Containerization or Auto scaling and some other options.

   <!--  ![custom](../../static/assets/img/documentImages/custom.png) -->

12. You can also apply the Idle termination on your selected resourcess for 30 minutes, 60 minutes and 90 minutes.
13. If you click on the 'instance', you will get c6i.xlarge by default for Master node and  compute node.
14. Along with this it will also create and auto mount FSX lustre on the master node.
15. Once you are done with your configuration selections, click on Launch and you will be asked for confirmation, once confirmed GROMACS application will get launched.
16. Once application is launched you can track the progress under 'Display Resources', which you will find on the 'Right side corner top, on the NUMEN Ui.

    ![displayResourcess](../../static/assets/img/documentImages/displayResourcess.png)

17. Once the resourcess are provisioned, you need to click on the 'link' symbol and you will get a DCV link, from where you can access the GROMACS Environment you just created.

    ![dcvlink](../../static/assets/img/documentImages/dcvlink.png)

18. We will Suggest you to select the 'CUSTOM LAUNCH' and select the Instance type as per requirements.
19. Select the Custom launch, and it will give you the landing page from where you can choose the instance types as per requirements.
20. NUMEN provides data relevant to the both the CROs , which is accessible under the ``/data``, directory.

## GROMACS TEST DATASET (Sample Test Job Run)

GROMACS has been tested with some pre-downloaded datsets which is available on below given links.

## DOWNLOADING THE DATA

Please click on the below link to download the protein data.

[Download Data From Here](https://www.rcsb.org/)

Using above link you can download any '.pdb' extention file.

In order to benchmark the perfomance, below example uses some additional db files you need to download as well.
Using below links you can download the sample data -

```

[1AKI.pdb](https://files.rcsb.org/download/1AKI.pdb)

[ions.mdp](http://www.mdtutorials.com/gmx/lysozyme/Files/ions.mdp)

[minim.mdp](http://www.mdtutorials.com/gmx/lysozyme/Files/minim.mdp)

[nvt.mdp](http://www.mdtutorials.com/gmx/lysozyme/Files/nvt.mdp)

[npt.mdp](http://www.mdtutorials.com/gmx/lysozyme/Files/npt.mdp)

[md.mdp](http://www.mdtutorials.com/gmx/lysozyme/Files/md.mdp)

```

## RUN SCRIPT

### [Single node]

Below is the sample run script which can be tweeked as per the requirements, with respect to the JOBs.

```

#!/bin/bash
#SBATCH --job-name=gromacs
#SBATCH --output=gmx-%j.out
#SBATCH --ntasks=2
#SBATCH --cpus-per-task=4
#SBATCH --time=24:00:00
#SBATCH --partition=compute
#SBATCH --ntasks-per-socket=1
sleep 60
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK

grep -v HOH 1AKI.pdb > 1AKI_clean.pdb
gmx_mpi pdb2gmx -f 1AKI_clean.pdb -o 1AKI_processed.gro -water spce
#select 15
echo "15"
gmx_mpi editconf -f 1AKI_processed.gro -o 1AKI_newbox.gro -c -d 1.0 -bt cubic
gmx_mpi solvate -cp 1AKI_newbox.gro -cs spc216.gro -o 1AKI_solv.gro -p topol.top
gmx_mpi grompp -f ions.mdp -c 1AKI_solv.gro -p topol.top -o ions.tpr
gmx_mpi genion -s ions.tpr -o 1AKI_solv_ions.gro -p topol.top -pname NA -nname CL -neutral
#select 13
echo "13"
gmx_mpi grompp -f minim.mdp -c 1AKI_solv_ions.gro -p topol.top -o em.tpr
gmx_mpi mdrun -v -deffnm em
gmx_mpi energy -f minim.edr -o potential.xvg
#enter 10 0
echo "10 0"
gmx_mpi grompp -f nvt.mdp -c em.gro -r em.gro -p topol.top -o nvt.tpr
gmx_mpi mdrun -deffnm nvt
gmx_mpi energy -f nvt.edr -o temperature.xvg
#enter 16 0
echo "16 0"
gmx_mpi grompp -f npt.mdp -c nvt.gro -r nvt.gro -t nvt.cpt -p topol.top -o npt.tpr
gmx_mpi mdrun -deffnm npt
gmx_mpi energy -f npt.edr -o pressure.xvg
#enter 18 0
echo "18 0"
gmx_mpi grompp -f md.mdp -c npt.gro -t npt.cpt -p topol.top -o md_0_1.tpr
gmx_mpi mdrun -deffnm md_0_1


```

## HOW TO RUN THE JOB ?

Below example contains the sample data which was used to ``Benchmark`` the Gromacs performance as well as step by step process followed to run the 'gromacs job' :

- Run

          - $ gmx_mpi --version

- Download the protein structure file with .pdb extention.
- (eg - https://www.rcsb.org/structure/1AK1)
- Hen egg white lysozyme (PDB code 1AKI)
- Once Download is done, (in order to strip out the crystal waters) to delete the residue "HOH" in
  the PDB file, you can use grep to delete these lines very easily(in Linux).

            $ grep -v HOH 1aki.pdb > 1AKI_clean.pdb

- Make sure that the PDB file should contain only protein atoms, and is ready to be input into the first GROMACS module, pdb2gmx.
- The purpose of pdb2gmx is to generate three files:

      	1.The topology for the molecule.
      	2.A position restraint file.
      	3.A post-processed structure file.

- Execute pdb2gmx by issuing the following command

       $ gmx pdb2gmx -f 1AKI_clean.pdb -o 1AKI_processed.gro -water spce

- The structure will be processed by pdb2gmx, and you will be prompted to choose a force field:

  ![SelectTheForceFeild](../../static/assets/img/documentImages/gromacsIMG/SelectTheForceFeild.png)

- In order to select all-atom OPLS force field, type 15 at the command prompt, followed by 'Enter'.
- The force field will contain the information that will be written to the topology.
- You have now generated three new files

       1. 1AKI_processed.gro
       2. topol.top
       3. posre.itp

- 1AKI_processed.gro is a GROMACS-formatted structure file that contains all the atoms defined within the force field.
- The topol.top file is the system topology.
- The posre.itp file contains information used to restrain the positions of heavy atoms.

- In this example, we are going to be simulating a simple aqueous system. It is possible to simulate proteins and other molecules
  in different solvents, provided that good parameters are available for all species involved.
- There are two steps to defining the box and filling it with solvent:

      1.Define the box dimensions using the editconf module.
      2.Fill the box with water using the solvate module (formerly called genbox).

- You are now presented with a choice as to how to treat the unit cell.
- Here we will use a simple cubic box as the unit cell.

- Let's define the box using editconf:

            $ gmx editconf -f 1AKI_processed.gro -o 1AKI_newbox.gro -c -d 1.0 -bt cubic

- Now that we have defined a box, we can fill it with solvent (water). Solvation is accomplished using solvate:

      		$ gmx solvate -cp 1AKI_newbox.gro -cs spc216.gro -o 1AKI_solv.gro -p topol.top

- in order to assemble your .tpr file run bellow command-
  $ gmx grompp -f ions.mdp -c 1AKI_solv.gro -p topol.top -o ions.tpr

- Now we have an atomic-level description of our system in the binary file ions.tpr. We will pass this file to genion:

            $ gmx genion -s ions.tpr -o 1AKI_solv_ions.gro -p topol.top -pname NA -nname CL -neutral

- When prompted, choose group 13 "SOL" for embedding ions.

            $ 13

- Assemble the binary input -

             $ gmx grompp -f minim.mdp -c 1AKI_solv_ions.gro -p topol.top -o em.tpr

- We are now ready to invoke mdrun to carry out the EM:

            $ gmx mdrun -v -deffnm em

- The em.edr file contains all of the energy terms that GROMACS collects during EM. You can analyze any .edr file using the GROMACS energy module:

            $ gmx energy -f em.edr -o potential.xvg

- At the prompt, type "10 0" to select Potential (10); zero (0) terminates input.

            $ 10 0

- We will call grompp and mdrun just as we did at the EM step:

            $ gmx grompp -f nvt.mdp -c em.gro -r em.gro -p topol.top -o nvt.tpr

      		$ gmx mdrun -deffnm nvt

- Let's analyze the temperature progression, again using energy:

            $ gmx energy -f nvt.edr -o temperature.xvg

- Type "16 0" at the prompt to select the temperature of the system and exit.

            $ 16 0

- We will call grompp and mdrun just as we did for NVT equilibration.

            $ gmx grompp -f npt.mdp -c nvt.gro -r nvt.gro -t nvt.cpt -p topol.top -o npt.tpr

      		$ gmx mdrun -deffnm npt

- To analyze the pressure progression

            $ gmx energy -f npt.edr -o pressure.xvg

- Type "18 0" at the prompt to select the pressure of the system and exit.

            $ 18 0

- Now Use energy and enter "24 0" at the prompt, to look the density as well -

             $ gmx energy -f npt.edr -o density.xvg

             $ 24 0

- Now run a 1-ns MD simulation

             $ gmx grompp -f md.mdp -c npt.gro -t npt.cpt -p topol.top -o md_0_1.tpr

- Now, execute mdrun:

               $ gmx mdrun -deffnm md_0_1

Assuming you have one GPU available, the mdrun command to make use of it is as simple as:

               $ gmx mdrun -deffnm md_0_1 -nb gpu

Expected time of run

![RunTime](../../static/assets/img/documentImages/gromacsIMG/RunTime.png)

### [Paralell Cluster]

In Order to run the 'Jobs' using paralell cluster you should Launch your application using paralell cluster.

Log in to the Head-Node using DCV link.

activate the gromacs environkment.

```
         $ spack env activate -p <EnvironmentName>
```

First, create a bash script "TestJob.sbatch" to submit jobs -

Below is the sample test job script to run Gromacs accross paralell cluster.

```
         #!/bin/bash
         #SBATCH --job-name=gromacs-hpc-numen
         #SBATCH --exclusive
         #SBATCH --output=/efshome/${USER_NAME}/mpi-outputfile.out
         #SBATCH --partition=hpc-numen
         #SBATCH -N 2
         NTOMP=1

         mkdir -p /efshome/${USER_NAME}/jobs/${SLURM_JOBID}
         cd /shared/jobs/${SLURM_JOBID}

         spack env ls
         spack env activate -p numen_gromacs-2022-2

         time mpirun -np 192 gmx_mpi mdrun -ntomp ${NTOMP} -s /
         efshome/$USER_NAME/<input-File> -resethway

```

you can submit the job using Below command-

         $ sbatch TestJob.sh

We can monitor the job state with watch squeue. Once it transitions into running we’ll see -

        $ watch squeue
        $ squeue -a
        $ sinfo -a
        $ sinfo -Nel : for details of nodes

these commands work individualy, from terminal.

![PcSlurmJobSubmissionJOB](../../static/assets/img/documentImages/gromacsIMG/PC/PcSlurmJobSubmissionJOB.png)

In the this image you can see the output sample for above mentioned commands.

Below is a sample slurm script to run Gromacs on 2 nodes and 20 cpu cores per node using MPI:

```
         #!/bin/bash
         #SBATCH -J gromacs_job
         #SBATCH -o gromacs_job.o%j
         #SBATCH -t 24:00:00
         #SBATCH -n 40 -N 2

         Spack env activate -p numen_gromacs-2022-2

         mpirun  mdrun_mpi -v -deffnm mytpr_file
```

© Clovertex, Inc. 2023, All rights reserved 
