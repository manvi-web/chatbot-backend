# MVP: Relion 3.1.x/4.0, cryoSPARC & Data Transfer

## SCOPE
This Document talks about the CryoSPARC deployment steps & processes involved in terms of NUMEN platform and which is the Standard Clovertex Practice.

## INTRODUCTION
CryoSPARC (Cryo-EM Single Particle Ab-Initio Reconstruction and Classification) is an Application HPC software solution for complete processing of single-particle cryo-electron microscopy (cryo-EM) data. 
CryoSPARC is useful for solving cryo-EM structures of membrane proteins, viruses, complexes, flexible molecules, small particles, phase plate data and negative stain data.
In NUMEN platform as per the Clovertex Standard Practice, every application deployment will be done through the code pipeline only.
## SOP
All the configurations are done using the Code Pipeline and Code Commit.
In terms of automating the flow of deployment we have created codes related to the configuration and managements of the required services in the code repositories.
All codes relevant to the deployment of Any application is stored in Code Commit, under the “ctx-ec2-image-builder” repository.

![](https://image-bucket-for-docs.s3.us-east-1.amazonaws.com/001.jpg?response-content-disposition=inline&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEGsaCmFwLXNvdXRoLTEiSDBGAiEAmSaTHfksOImEDDld8XqjxLzBhkknWnlNltVSF79HxFUCIQCIdzwxU0Cb4vkEbcCLk5DBgj1rjEc0pCOx15sOuaw4RSqMBAjE%2F%2F%2F%2F%2F%2F%2F%2F%2F%2F8BEAEaDDY1ODkwNzM4MDIxMyIMr0lAOLK5Tk3fMSgQKuAD6uRvxnqcfDyUWtCYvqdGEXEXlUNByFgUovRJFlNkcMZSYenQPNRQidLBOiba1GuRxCofAo%2FHfkyIVjRmkWXvPtD%2BYxUjAVGNEtN8pOT61JgN7oqmASQwrCiu6PsSSN%2FVVOi4UjMiXpOtHnAqqulTow6UyseoPNG7uyrA%2FL8VOiB2WifMGh0HV02DPK6T2EJg6UHIVYkdlAxN6scMsH9HQVe7ONzxZsYSS9N0Pu7nTAq1XqHtjHGg5pjTbPkCvbmgNDDcFAWnH2XyQHq5u3fEs8S3AQcBH5yppwUvMmFG%2BfJIJzemYRInkssZ6oqfE761G%2Bfb3BL204um8psNvXZcoNnHKhYq91TFTmSUF5AG%2BUpqPOAbvK6thbIxlauRKtsHMoxlatzUzd5Tl6cFiOVPuCwyhOlrk8Gl0hN%2B3DPC3dfYExhLpaQ2EdseeUvIbu6Mwmmr79BZmojWYM4%2FQ9Ujd4DONVdyN%2FW0vs7QAxO4kYjT5dw0NVDmrpXrjZW8neXJaJQlFyy5qme2ZuAghtcwJy0lrvMr5H8TuJ5ubHKzK%2BKl0%2FQqibIj2AB0KfERShMCWjzcoTP1CXotdbNnYxq71hB2c4Rmp8RKVYUbyr4uCc2xt8vHXMMWIXt7bCMvqn6RMLTStZcGOpMCMUd3XzPnkY2R%2BM4N1Vx8Nuk%2B%2BWBj8qMp5ZpnTwC3fg4YhGrlePj8E%2BrDRF1%2FwPn%2B7OMXTjqFu5Xga2RZ4vHlzWQR0%2B5mMTPUlsc%2BIJ%2Fh%2Fp8xnySOiDlSTYzDSsE%2Fg2fNTrlyfiQjefRBwOZ3FDh0I%2FHuSqTL4c0HH1BtUEyBIieObCwCQaHGbYjPyH6uCNBgySuedp18JHIIklXTZpWAxGiV1iXo3on7w97po0ubz0shG8LvaqCoMu76DDcYMoJ6I75HyvtaDrZgXSkqpd5fpKm65IKKG2cAhsC%2FJWNV3qG5HoZC%2FIka3EmGBmbuwL%2BZjaEG7vyHzrnCcL9d1A5aoCyQNAXKUfr1dR7Iw25BIjYb3l8%3D&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Date=20220805T194220Z&X-Amz-SignedHeaders=host&X-Amz-Expires=300&X-Amz-Credential=ASIAZS2PQXH2XS7IXPOA%2F20220805%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Signature=ef1e4f67a2a77f4a85c33d6d736788a3f86b838eb4c94d571a634c46e37ed447)

## RELION 3.x OR 4.0 DEPLOYMENT
To deploy the any HPC application software, we have respective codes in the code repository.
![](https://image-bucket-for-docs.s3.us-east-1.amazonaws.com/002.jpg?response-content-disposition=inline&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEGsaCmFwLXNvdXRoLTEiSDBGAiEAmSaTHfksOImEDDld8XqjxLzBhkknWnlNltVSF79HxFUCIQCIdzwxU0Cb4vkEbcCLk5DBgj1rjEc0pCOx15sOuaw4RSqMBAjE%2F%2F%2F%2F%2F%2F%2F%2F%2F%2F8BEAEaDDY1ODkwNzM4MDIxMyIMr0lAOLK5Tk3fMSgQKuAD6uRvxnqcfDyUWtCYvqdGEXEXlUNByFgUovRJFlNkcMZSYenQPNRQidLBOiba1GuRxCofAo%2FHfkyIVjRmkWXvPtD%2BYxUjAVGNEtN8pOT61JgN7oqmASQwrCiu6PsSSN%2FVVOi4UjMiXpOtHnAqqulTow6UyseoPNG7uyrA%2FL8VOiB2WifMGh0HV02DPK6T2EJg6UHIVYkdlAxN6scMsH9HQVe7ONzxZsYSS9N0Pu7nTAq1XqHtjHGg5pjTbPkCvbmgNDDcFAWnH2XyQHq5u3fEs8S3AQcBH5yppwUvMmFG%2BfJIJzemYRInkssZ6oqfE761G%2Bfb3BL204um8psNvXZcoNnHKhYq91TFTmSUF5AG%2BUpqPOAbvK6thbIxlauRKtsHMoxlatzUzd5Tl6cFiOVPuCwyhOlrk8Gl0hN%2B3DPC3dfYExhLpaQ2EdseeUvIbu6Mwmmr79BZmojWYM4%2FQ9Ujd4DONVdyN%2FW0vs7QAxO4kYjT5dw0NVDmrpXrjZW8neXJaJQlFyy5qme2ZuAghtcwJy0lrvMr5H8TuJ5ubHKzK%2BKl0%2FQqibIj2AB0KfERShMCWjzcoTP1CXotdbNnYxq71hB2c4Rmp8RKVYUbyr4uCc2xt8vHXMMWIXt7bCMvqn6RMLTStZcGOpMCMUd3XzPnkY2R%2BM4N1Vx8Nuk%2B%2BWBj8qMp5ZpnTwC3fg4YhGrlePj8E%2BrDRF1%2FwPn%2B7OMXTjqFu5Xga2RZ4vHlzWQR0%2B5mMTPUlsc%2BIJ%2Fh%2Fp8xnySOiDlSTYzDSsE%2Fg2fNTrlyfiQjefRBwOZ3FDh0I%2FHuSqTL4c0HH1BtUEyBIieObCwCQaHGbYjPyH6uCNBgySuedp18JHIIklXTZpWAxGiV1iXo3on7w97po0ubz0shG8LvaqCoMu76DDcYMoJ6I75HyvtaDrZgXSkqpd5fpKm65IKKG2cAhsC%2FJWNV3qG5HoZC%2FIka3EmGBmbuwL%2BZjaEG7vyHzrnCcL9d1A5aoCyQNAXKUfr1dR7Iw25BIjYb3l8%3D&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Date=20220805T194559Z&X-Amz-SignedHeaders=host&X-Amz-Expires=300&X-Amz-Credential=ASIAZS2PQXH2XS7IXPOA%2F20220805%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Signature=802ae0c1f19c4a2de7f48e218b7cb3d8aec79ca2c38dcdb0e0ab26f3360c2bda)

There are two major pipelines involved with different code recipes which are parameterized with the deployment environments, along with all desired variables.
These code recipes are specific YAML templates, containing deployment flow along with referring the codes and parameter files being used during the whole deployment process.

As per the Clovertex Standard Practices, below are the two major Pipelines we use –
1.	CODE PIPELINE
2.	EC2 IMAGE BUILDER PIPLINE


## CODE PIPELINE
•	The code pipeline is responsible for creation of another pipeline as “Ec2 image builder pipeline”.

•	This will be used to create the OS image for the master and compute node of the parallel cluster.

•	There are four stages in this pipeline, Source, Approval, Build and Deploy.

•	When deploying this pipeline, it will read the source code from respective repository and once it has the approval, it will deploy the Ec2 image builder pipeline.


## IMAGE BUILDER CODE PIPLINE
Image builder pipeline contains following stages -
![](https://image-bucket-for-docs.s3.us-east-1.amazonaws.com/004.jpg?response-content-disposition=inline&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEGsaCmFwLXNvdXRoLTEiSDBGAiEAmSaTHfksOImEDDld8XqjxLzBhkknWnlNltVSF79HxFUCIQCIdzwxU0Cb4vkEbcCLk5DBgj1rjEc0pCOx15sOuaw4RSqMBAjE%2F%2F%2F%2F%2F%2F%2F%2F%2F%2F8BEAEaDDY1ODkwNzM4MDIxMyIMr0lAOLK5Tk3fMSgQKuAD6uRvxnqcfDyUWtCYvqdGEXEXlUNByFgUovRJFlNkcMZSYenQPNRQidLBOiba1GuRxCofAo%2FHfkyIVjRmkWXvPtD%2BYxUjAVGNEtN8pOT61JgN7oqmASQwrCiu6PsSSN%2FVVOi4UjMiXpOtHnAqqulTow6UyseoPNG7uyrA%2FL8VOiB2WifMGh0HV02DPK6T2EJg6UHIVYkdlAxN6scMsH9HQVe7ONzxZsYSS9N0Pu7nTAq1XqHtjHGg5pjTbPkCvbmgNDDcFAWnH2XyQHq5u3fEs8S3AQcBH5yppwUvMmFG%2BfJIJzemYRInkssZ6oqfE761G%2Bfb3BL204um8psNvXZcoNnHKhYq91TFTmSUF5AG%2BUpqPOAbvK6thbIxlauRKtsHMoxlatzUzd5Tl6cFiOVPuCwyhOlrk8Gl0hN%2B3DPC3dfYExhLpaQ2EdseeUvIbu6Mwmmr79BZmojWYM4%2FQ9Ujd4DONVdyN%2FW0vs7QAxO4kYjT5dw0NVDmrpXrjZW8neXJaJQlFyy5qme2ZuAghtcwJy0lrvMr5H8TuJ5ubHKzK%2BKl0%2FQqibIj2AB0KfERShMCWjzcoTP1CXotdbNnYxq71hB2c4Rmp8RKVYUbyr4uCc2xt8vHXMMWIXt7bCMvqn6RMLTStZcGOpMCMUd3XzPnkY2R%2BM4N1Vx8Nuk%2B%2BWBj8qMp5ZpnTwC3fg4YhGrlePj8E%2BrDRF1%2FwPn%2B7OMXTjqFu5Xga2RZ4vHlzWQR0%2B5mMTPUlsc%2BIJ%2Fh%2Fp8xnySOiDlSTYzDSsE%2Fg2fNTrlyfiQjefRBwOZ3FDh0I%2FHuSqTL4c0HH1BtUEyBIieObCwCQaHGbYjPyH6uCNBgySuedp18JHIIklXTZpWAxGiV1iXo3on7w97po0ubz0shG8LvaqCoMu76DDcYMoJ6I75HyvtaDrZgXSkqpd5fpKm65IKKG2cAhsC%2FJWNV3qG5HoZC%2FIka3EmGBmbuwL%2BZjaEG7vyHzrnCcL9d1A5aoCyQNAXKUfr1dR7Iw25BIjYb3l8%3D&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Date=20220805T195757Z&X-Amz-SignedHeaders=host&X-Amz-Expires=300&X-Amz-Credential=ASIAZS2PQXH2XS7IXPOA%2F20220805%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Signature=5bc133f3e542c695a58457b282939d6b4734474af10baa14984a313b63464390)

### SOURCE STAGE
When the developer push commits to the repository, Code Pipeline detects the pushed changes, and a pipeline execution starts from the Source Stage.

### MANUAL APPROVAL STAGE
Once the Source action completes successfully, the pipeline execution transitions from Source Stage to Manual Approval stage. In general, the Manual Approval Stage contains two approvals action. i.e., Approve and reject. 
When a pipeline includes an approval action, the pipeline execution stops at the point where the action has been added. The pipeline won’t resume unless someone manually approves the action. If an approver rejects the action, or if no approval response is received within seven days of the pipeline stopping for the approval action, the pipeline status becomes Failed.

### BUILD STAGE
In build stage will run some concurrent set of commands using various configuration files specified under CODEBUILD_SRC_DIR location.
This stage includes PRE_BUILD, BUILD and POST_BUILD as sub-stages.

### DEPLOY STAGE
In deploy stage, image builder pipeline will create the CloudFormation stack for Infrastructure relevant to the pipeline, from configuration YAML file. Such as ec2 image builder resources like Image Pipeline, Infrastructure Configuration, Distribution Configuration, Image Recipe, Components.
To track the progress of the CF stack, please navigate to the Cloud Formation console.
Once you click on the ‘Details’ under the ‘Deploy’ stage, you will be diverted to the Cloud Formation console in AWS account.

![](https://image-bucket-for-docs.s3.us-east-1.amazonaws.com/005.jpg?response-content-disposition=inline&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEGsaCmFwLXNvdXRoLTEiSDBGAiEAmSaTHfksOImEDDld8XqjxLzBhkknWnlNltVSF79HxFUCIQCIdzwxU0Cb4vkEbcCLk5DBgj1rjEc0pCOx15sOuaw4RSqMBAjE%2F%2F%2F%2F%2F%2F%2F%2F%2F%2F8BEAEaDDY1ODkwNzM4MDIxMyIMr0lAOLK5Tk3fMSgQKuAD6uRvxnqcfDyUWtCYvqdGEXEXlUNByFgUovRJFlNkcMZSYenQPNRQidLBOiba1GuRxCofAo%2FHfkyIVjRmkWXvPtD%2BYxUjAVGNEtN8pOT61JgN7oqmASQwrCiu6PsSSN%2FVVOi4UjMiXpOtHnAqqulTow6UyseoPNG7uyrA%2FL8VOiB2WifMGh0HV02DPK6T2EJg6UHIVYkdlAxN6scMsH9HQVe7ONzxZsYSS9N0Pu7nTAq1XqHtjHGg5pjTbPkCvbmgNDDcFAWnH2XyQHq5u3fEs8S3AQcBH5yppwUvMmFG%2BfJIJzemYRInkssZ6oqfE761G%2Bfb3BL204um8psNvXZcoNnHKhYq91TFTmSUF5AG%2BUpqPOAbvK6thbIxlauRKtsHMoxlatzUzd5Tl6cFiOVPuCwyhOlrk8Gl0hN%2B3DPC3dfYExhLpaQ2EdseeUvIbu6Mwmmr79BZmojWYM4%2FQ9Ujd4DONVdyN%2FW0vs7QAxO4kYjT5dw0NVDmrpXrjZW8neXJaJQlFyy5qme2ZuAghtcwJy0lrvMr5H8TuJ5ubHKzK%2BKl0%2FQqibIj2AB0KfERShMCWjzcoTP1CXotdbNnYxq71hB2c4Rmp8RKVYUbyr4uCc2xt8vHXMMWIXt7bCMvqn6RMLTStZcGOpMCMUd3XzPnkY2R%2BM4N1Vx8Nuk%2B%2BWBj8qMp5ZpnTwC3fg4YhGrlePj8E%2BrDRF1%2FwPn%2B7OMXTjqFu5Xga2RZ4vHlzWQR0%2B5mMTPUlsc%2BIJ%2Fh%2Fp8xnySOiDlSTYzDSsE%2Fg2fNTrlyfiQjefRBwOZ3FDh0I%2FHuSqTL4c0HH1BtUEyBIieObCwCQaHGbYjPyH6uCNBgySuedp18JHIIklXTZpWAxGiV1iXo3on7w97po0ubz0shG8LvaqCoMu76DDcYMoJ6I75HyvtaDrZgXSkqpd5fpKm65IKKG2cAhsC%2FJWNV3qG5HoZC%2FIka3EmGBmbuwL%2BZjaEG7vyHzrnCcL9d1A5aoCyQNAXKUfr1dR7Iw25BIjYb3l8%3D&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Date=20220805T200203Z&X-Amz-SignedHeaders=host&X-Amz-Expires=300&X-Amz-Credential=ASIAZS2PQXH2XS7IXPOA%2F20220805%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Signature=4edd9bb33a69eda04b50c3a4cc64f2bbcb76fa11b6bdcf2cbe8c270358e2a23f)

![](https://image-bucket-for-docs.s3.us-east-1.amazonaws.com/006.jpg?response-content-disposition=inline&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEGsaCmFwLXNvdXRoLTEiSDBGAiEAmSaTHfksOImEDDld8XqjxLzBhkknWnlNltVSF79HxFUCIQCIdzwxU0Cb4vkEbcCLk5DBgj1rjEc0pCOx15sOuaw4RSqMBAjE%2F%2F%2F%2F%2F%2F%2F%2F%2F%2F8BEAEaDDY1ODkwNzM4MDIxMyIMr0lAOLK5Tk3fMSgQKuAD6uRvxnqcfDyUWtCYvqdGEXEXlUNByFgUovRJFlNkcMZSYenQPNRQidLBOiba1GuRxCofAo%2FHfkyIVjRmkWXvPtD%2BYxUjAVGNEtN8pOT61JgN7oqmASQwrCiu6PsSSN%2FVVOi4UjMiXpOtHnAqqulTow6UyseoPNG7uyrA%2FL8VOiB2WifMGh0HV02DPK6T2EJg6UHIVYkdlAxN6scMsH9HQVe7ONzxZsYSS9N0Pu7nTAq1XqHtjHGg5pjTbPkCvbmgNDDcFAWnH2XyQHq5u3fEs8S3AQcBH5yppwUvMmFG%2BfJIJzemYRInkssZ6oqfE761G%2Bfb3BL204um8psNvXZcoNnHKhYq91TFTmSUF5AG%2BUpqPOAbvK6thbIxlauRKtsHMoxlatzUzd5Tl6cFiOVPuCwyhOlrk8Gl0hN%2B3DPC3dfYExhLpaQ2EdseeUvIbu6Mwmmr79BZmojWYM4%2FQ9Ujd4DONVdyN%2FW0vs7QAxO4kYjT5dw0NVDmrpXrjZW8neXJaJQlFyy5qme2ZuAghtcwJy0lrvMr5H8TuJ5ubHKzK%2BKl0%2FQqibIj2AB0KfERShMCWjzcoTP1CXotdbNnYxq71hB2c4Rmp8RKVYUbyr4uCc2xt8vHXMMWIXt7bCMvqn6RMLTStZcGOpMCMUd3XzPnkY2R%2BM4N1Vx8Nuk%2B%2BWBj8qMp5ZpnTwC3fg4YhGrlePj8E%2BrDRF1%2FwPn%2B7OMXTjqFu5Xga2RZ4vHlzWQR0%2B5mMTPUlsc%2BIJ%2Fh%2Fp8xnySOiDlSTYzDSsE%2Fg2fNTrlyfiQjefRBwOZ3FDh0I%2FHuSqTL4c0HH1BtUEyBIieObCwCQaHGbYjPyH6uCNBgySuedp18JHIIklXTZpWAxGiV1iXo3on7w97po0ubz0shG8LvaqCoMu76DDcYMoJ6I75HyvtaDrZgXSkqpd5fpKm65IKKG2cAhsC%2FJWNV3qG5HoZC%2FIka3EmGBmbuwL%2BZjaEG7vyHzrnCcL9d1A5aoCyQNAXKUfr1dR7Iw25BIjYb3l8%3D&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Date=20220805T200331Z&X-Amz-SignedHeaders=host&X-Amz-Expires=300&X-Amz-Credential=ASIAZS2PQXH2XS7IXPOA%2F20220805%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Signature=8ee0f5d3561ea8b56e90952ed4b0565330a1fb8aa9566e5dd430b240bd1be483)

### EC2 IMAGE BUILDER PIPLINE
EC2 Image Builder is a fully managed AWS service that makes it easier to automate the creation, management, and deployment of customized, secure, and up-to-date server images that are pre-installed and pre-configured with software and settings to meet specific requirements.

There are three main stages under the Ec2 image builder pipeline as – 

1.	Recipe
2.	Infrastructure Configuration
3.	Region Distribution Settings 

### RECIPE
The selected base image and components make up an image recipe.
The base image for Ec2 image builder is the Centos Image for Parallel Cluster released by AWS, as an example concerning the parallel cluster version, we must choose the AMI image for Parallel Cluster as the base image as part of our Ec2 image builder recipe then it installs Development Tools, Kernel headers, and Kernel development packages, CUDA (version 11.0,11.3 & 11.5) and Nvidia driver.

It also creates the user ‘cryosparcuser’ for the CryoSPARC application and then installs
 all the security patches available.

## IMAGE BUILDING PROCESS FLOW
To create a new image, first need to make the changes in the (ImageVersion.json) file,
and change the version number as required and make the commit.

![](https://image-bucket-for-docs.s3.us-east-1.amazonaws.com/007.jpg?response-content-disposition=inline&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEGsaCmFwLXNvdXRoLTEiSDBGAiEAmSaTHfksOImEDDld8XqjxLzBhkknWnlNltVSF79HxFUCIQCIdzwxU0Cb4vkEbcCLk5DBgj1rjEc0pCOx15sOuaw4RSqMBAjE%2F%2F%2F%2F%2F%2F%2F%2F%2F%2F8BEAEaDDY1ODkwNzM4MDIxMyIMr0lAOLK5Tk3fMSgQKuAD6uRvxnqcfDyUWtCYvqdGEXEXlUNByFgUovRJFlNkcMZSYenQPNRQidLBOiba1GuRxCofAo%2FHfkyIVjRmkWXvPtD%2BYxUjAVGNEtN8pOT61JgN7oqmASQwrCiu6PsSSN%2FVVOi4UjMiXpOtHnAqqulTow6UyseoPNG7uyrA%2FL8VOiB2WifMGh0HV02DPK6T2EJg6UHIVYkdlAxN6scMsH9HQVe7ONzxZsYSS9N0Pu7nTAq1XqHtjHGg5pjTbPkCvbmgNDDcFAWnH2XyQHq5u3fEs8S3AQcBH5yppwUvMmFG%2BfJIJzemYRInkssZ6oqfE761G%2Bfb3BL204um8psNvXZcoNnHKhYq91TFTmSUF5AG%2BUpqPOAbvK6thbIxlauRKtsHMoxlatzUzd5Tl6cFiOVPuCwyhOlrk8Gl0hN%2B3DPC3dfYExhLpaQ2EdseeUvIbu6Mwmmr79BZmojWYM4%2FQ9Ujd4DONVdyN%2FW0vs7QAxO4kYjT5dw0NVDmrpXrjZW8neXJaJQlFyy5qme2ZuAghtcwJy0lrvMr5H8TuJ5ubHKzK%2BKl0%2FQqibIj2AB0KfERShMCWjzcoTP1CXotdbNnYxq71hB2c4Rmp8RKVYUbyr4uCc2xt8vHXMMWIXt7bCMvqn6RMLTStZcGOpMCMUd3XzPnkY2R%2BM4N1Vx8Nuk%2B%2BWBj8qMp5ZpnTwC3fg4YhGrlePj8E%2BrDRF1%2FwPn%2B7OMXTjqFu5Xga2RZ4vHlzWQR0%2B5mMTPUlsc%2BIJ%2Fh%2Fp8xnySOiDlSTYzDSsE%2Fg2fNTrlyfiQjefRBwOZ3FDh0I%2FHuSqTL4c0HH1BtUEyBIieObCwCQaHGbYjPyH6uCNBgySuedp18JHIIklXTZpWAxGiV1iXo3on7w97po0ubz0shG8LvaqCoMu76DDcYMoJ6I75HyvtaDrZgXSkqpd5fpKm65IKKG2cAhsC%2FJWNV3qG5HoZC%2FIka3EmGBmbuwL%2BZjaEG7vyHzrnCcL9d1A5aoCyQNAXKUfr1dR7Iw25BIjYb3l8%3D&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Date=20220805T200733Z&X-Amz-SignedHeaders=host&X-Amz-Expires=300&X-Amz-Credential=ASIAZS2PQXH2XS7IXPOA%2F20220805%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Signature=cb88d4843ccaeef0fb15c7809e65351cf3929ac73dd578a38ecd817dbcea2eed)

Once it is done, we must run the pipeline” ctx-numen-imagebuilder-relionv312-ubuntu2004-f1dev”, for this go to Code Pipeline “ctx-numen-imagebuilder-relionv312-ubuntu2004-f1dev” and navigate to Actions and ‘Run Pipeline’ and provide approval for the build stage.

![](https://image-bucket-for-docs.s3.us-east-1.amazonaws.com/008.jpg?response-content-disposition=inline&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEGsaCmFwLXNvdXRoLTEiSDBGAiEAmSaTHfksOImEDDld8XqjxLzBhkknWnlNltVSF79HxFUCIQCIdzwxU0Cb4vkEbcCLk5DBgj1rjEc0pCOx15sOuaw4RSqMBAjE%2F%2F%2F%2F%2F%2F%2F%2F%2F%2F8BEAEaDDY1ODkwNzM4MDIxMyIMr0lAOLK5Tk3fMSgQKuAD6uRvxnqcfDyUWtCYvqdGEXEXlUNByFgUovRJFlNkcMZSYenQPNRQidLBOiba1GuRxCofAo%2FHfkyIVjRmkWXvPtD%2BYxUjAVGNEtN8pOT61JgN7oqmASQwrCiu6PsSSN%2FVVOi4UjMiXpOtHnAqqulTow6UyseoPNG7uyrA%2FL8VOiB2WifMGh0HV02DPK6T2EJg6UHIVYkdlAxN6scMsH9HQVe7ONzxZsYSS9N0Pu7nTAq1XqHtjHGg5pjTbPkCvbmgNDDcFAWnH2XyQHq5u3fEs8S3AQcBH5yppwUvMmFG%2BfJIJzemYRInkssZ6oqfE761G%2Bfb3BL204um8psNvXZcoNnHKhYq91TFTmSUF5AG%2BUpqPOAbvK6thbIxlauRKtsHMoxlatzUzd5Tl6cFiOVPuCwyhOlrk8Gl0hN%2B3DPC3dfYExhLpaQ2EdseeUvIbu6Mwmmr79BZmojWYM4%2FQ9Ujd4DONVdyN%2FW0vs7QAxO4kYjT5dw0NVDmrpXrjZW8neXJaJQlFyy5qme2ZuAghtcwJy0lrvMr5H8TuJ5ubHKzK%2BKl0%2FQqibIj2AB0KfERShMCWjzcoTP1CXotdbNnYxq71hB2c4Rmp8RKVYUbyr4uCc2xt8vHXMMWIXt7bCMvqn6RMLTStZcGOpMCMUd3XzPnkY2R%2BM4N1Vx8Nuk%2B%2BWBj8qMp5ZpnTwC3fg4YhGrlePj8E%2BrDRF1%2FwPn%2B7OMXTjqFu5Xga2RZ4vHlzWQR0%2B5mMTPUlsc%2BIJ%2Fh%2Fp8xnySOiDlSTYzDSsE%2Fg2fNTrlyfiQjefRBwOZ3FDh0I%2FHuSqTL4c0HH1BtUEyBIieObCwCQaHGbYjPyH6uCNBgySuedp18JHIIklXTZpWAxGiV1iXo3on7w97po0ubz0shG8LvaqCoMu76DDcYMoJ6I75HyvtaDrZgXSkqpd5fpKm65IKKG2cAhsC%2FJWNV3qG5HoZC%2FIka3EmGBmbuwL%2BZjaEG7vyHzrnCcL9d1A5aoCyQNAXKUfr1dR7Iw25BIjYb3l8%3D&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Date=20220805T200926Z&X-Amz-SignedHeaders=host&X-Amz-Expires=300&X-Amz-Credential=ASIAZS2PQXH2XS7IXPOA%2F20220805%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Signature=96bdcba01cf526df3103b6febcea146e7f4feb405f879573dcec4594e04d81bb)

This pipeline provides a build environment for ubuntu2004 with relionv312.
Once the process completes at the end of the code build pipeline, it will create an AMI with the respective version.


Go to Images to view the images created.

![](https://image-bucket-for-docs.s3.us-east-1.amazonaws.com/009.jpg?response-content-disposition=inline&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEGsaCmFwLXNvdXRoLTEiSDBGAiEAmSaTHfksOImEDDld8XqjxLzBhkknWnlNltVSF79HxFUCIQCIdzwxU0Cb4vkEbcCLk5DBgj1rjEc0pCOx15sOuaw4RSqMBAjE%2F%2F%2F%2F%2F%2F%2F%2F%2F%2F8BEAEaDDY1ODkwNzM4MDIxMyIMr0lAOLK5Tk3fMSgQKuAD6uRvxnqcfDyUWtCYvqdGEXEXlUNByFgUovRJFlNkcMZSYenQPNRQidLBOiba1GuRxCofAo%2FHfkyIVjRmkWXvPtD%2BYxUjAVGNEtN8pOT61JgN7oqmASQwrCiu6PsSSN%2FVVOi4UjMiXpOtHnAqqulTow6UyseoPNG7uyrA%2FL8VOiB2WifMGh0HV02DPK6T2EJg6UHIVYkdlAxN6scMsH9HQVe7ONzxZsYSS9N0Pu7nTAq1XqHtjHGg5pjTbPkCvbmgNDDcFAWnH2XyQHq5u3fEs8S3AQcBH5yppwUvMmFG%2BfJIJzemYRInkssZ6oqfE761G%2Bfb3BL204um8psNvXZcoNnHKhYq91TFTmSUF5AG%2BUpqPOAbvK6thbIxlauRKtsHMoxlatzUzd5Tl6cFiOVPuCwyhOlrk8Gl0hN%2B3DPC3dfYExhLpaQ2EdseeUvIbu6Mwmmr79BZmojWYM4%2FQ9Ujd4DONVdyN%2FW0vs7QAxO4kYjT5dw0NVDmrpXrjZW8neXJaJQlFyy5qme2ZuAghtcwJy0lrvMr5H8TuJ5ubHKzK%2BKl0%2FQqibIj2AB0KfERShMCWjzcoTP1CXotdbNnYxq71hB2c4Rmp8RKVYUbyr4uCc2xt8vHXMMWIXt7bCMvqn6RMLTStZcGOpMCMUd3XzPnkY2R%2BM4N1Vx8Nuk%2B%2BWBj8qMp5ZpnTwC3fg4YhGrlePj8E%2BrDRF1%2FwPn%2B7OMXTjqFu5Xga2RZ4vHlzWQR0%2B5mMTPUlsc%2BIJ%2Fh%2Fp8xnySOiDlSTYzDSsE%2Fg2fNTrlyfiQjefRBwOZ3FDh0I%2FHuSqTL4c0HH1BtUEyBIieObCwCQaHGbYjPyH6uCNBgySuedp18JHIIklXTZpWAxGiV1iXo3on7w97po0ubz0shG8LvaqCoMu76DDcYMoJ6I75HyvtaDrZgXSkqpd5fpKm65IKKG2cAhsC%2FJWNV3qG5HoZC%2FIka3EmGBmbuwL%2BZjaEG7vyHzrnCcL9d1A5aoCyQNAXKUfr1dR7Iw25BIjYb3l8%3D&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Date=20220805T201146Z&X-Amz-SignedHeaders=host&X-Amz-Expires=300&X-Amz-Credential=ASIAZS2PQXH2XS7IXPOA%2F20220805%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Signature=9e6be0296ebbf8fda14d0f70b2f3f3e108fac9608ff60d81bd0d9b4effe16777)




## DEPLOYMENT STEPS
1.	Navigate to the cloud9 IDE terminal.
2.	Switch to the “ctx-hpc-ec2-image-builder-allinone” branch.
3.	Under ‘parameter’ directory, open the parameter file ‘ctx-hpc-relionv312-ubuntu2004.json’, and check for the Parameters.
4.	This file contains mandatory parameters for the application deployment, if any one of it is missing the build will fail.
5.	Once validating the parameter file, run the ‘deploy_ec2_image_builder_cft.sh’ bash file along with parameter files mentioned above.
$ sh deploy_ec2_image_builder_cft.sh parameters/ ctx-hpc-relionv312-ubuntu2004.json
6.	Once you run the ‘cft.sh’ script it will use pointed parameters and will deploy a Code Pipeline.
7.	Navigate to the AWS console – Code Pipeline and provide the Approval.
8.	Once Approval is provided, build stage will start.
9.	Once the Build is completed, it will enter Deploy stage.
10.	At the end of the ‘Deploy’ stage of code pipeline, it will create an Ec2 image builder pipeline.
11.	Navigate to the ‘Ec2 Image Builder’ console and monitor the Image pipeline.
12.	Select the respective pipeline, navigate to ‘Actions’, and ‘Run the Pipeline’.
13.	Once the ‘Run’ will complete, it will create an ‘AMI’ containing the required Application, along with the new version of the AMI.





