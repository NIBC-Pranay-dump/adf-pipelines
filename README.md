# ADF Pipelines
Template for Azure Data Factory ci/cd pipeline + some pre-setup linked services.

Includes:
- a cicd pipeline which uses the MS provided node package to replace the "publish" button which a ci/cd pipeline.
- a linked service to a keyvault (which requires passing a global variable, keyvault_uri).
- a linked service to the raw_ingest database in a datamart (which requires passing a global variable, the keyvault_uri of the datamart you want to use).
- a linked service to a storage account (which requires passing a global variable storage_account_uri).
- a dataset to a table in the raw_ingest database (requires the same keyvault_uri to the datamart you want to use).
- a dataset to a json dataset stored in a blobstore (requires the storage_account_uri).
- a dataset to a parquest dataset stored in a blobstore (require the storage_account_uri).

## Initial setup
After deploying the platform, git link the udev adf instance. Then follow these steps:
1. Go to the udev adf instance
1. Disconnect it from git manually
1. Connect it to git, and make sure to import existing resources into the main/master branch
1. Go to you git repo, and add the files from this template

## Data plaform / Data warehouse
Not all datasets/linked services are applicable to each environment. Delete them as you see fit.

## How to use
The different linked services etc, are pretty much self explanatory. But the way-of-working is slightly different.
We do not make use of the "Publish" button in ADF. Eg, after merging your feature branch into main/master, the ci/cd pipeline will take care of the rest.
Adding another global parameter has to be done using the data platform terraform code. As it controls the global parameter list of the adf instances.
A manual change to the global parameter list will be overwritten by a deployment of the data platform. Eg, there is no other option then to use that pipeline to set them.
