# Troubleshooting Guide

## Scope
This document is about NUMEN platform version 1.0. 

# Troubleshooting
1. I a new user joined to my team, I don't know how to add a new user to the environment?
  1. In the main account
     1. Go to AWS Identity Center
     1. Make sure the user is created under users 
     1. Select Applications -> Numen v1.0 (Prod)
     1. Select Assign Users
     1. Search and add user and save
  1. In the Prod account, document steps to add into Cognito pool
 

1. I have changed something and my system is not working?
   1. Simply terminate the instance and launch a new one

1. I have uploaded file(s) into S3 bucket directly, but can not read it from the Linux OS?
   1. If the files are added into /projects folder and came up with the wrong permissions, please follow steps below to reset permissions
   

© Clovertex, Inc. 2023, All rights reserved.
