# Release Notes

## Scope
This document is about NUMEN platform version 1.0. 

## Known Issues
1. Relion v3.1.3 running on Amazon Linux 2 with GPU build failed thus not working
1. Relion v3.1.3 running on Ubuntu 20.0 with GPU build failed thus not working
1. Relion v4.0.0 running on Ubuntu 20.0 with GPU build failed thus not working
1. AWS Identity Center SSO integration with Cognito/Numen is not working. See the temporary fix/workaround below


## Fixes
1. AWS Identity Center SSO integration with Cognito/Numen is not working 
   1. Numen is utilizing Cognito user pools as interim solution. 
   1. Clovertex is working on this issue and once resolved, we will schedule with you to update your configuration. 

## Features
1. Generic Linux as an application to deploy
1. Instance details table
1. Documentation updates
1. Latest CPU/GPU support
1. Data and Projects as default for all instances
1. Home directory on /efshome/$USER as default for all instances
1. Multiple instance type selection e.g. small, medium, large for each Parallel Cluster queue
1. GPU count based selection for the Parallel Cluster queue
1. Budget integration per user monthly recurring
1. Firefox browser is installed on Ubuntu
1. Chromium browser is installed on Amazon Linux 2
1. Specific user can be added into sudoers list
1. xterm is installed on both Ubuntu and Amazon Linux 2
1. Share/Unshare application instances with others in the platform


## Upcoming Features
1. FSx for Lustre automation and alerting 

© Clovertex, Inc. 2023, All rights reserved.
