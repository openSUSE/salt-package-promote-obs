# salt-package-promote-obs

This repository tracks the Jenkins pipelines, and scripts that we use at SUSE to promote the Salt packages used in our products.

## Jenkinsfile_promote_salt_packages

This pipeline takes care of promoting the classic Salt packages and dependencies at [OBS](https://build.opensuse.org/):

- [systemsmanagement:saltstack:products:testing](https://build.opensuse.org/project/show/systemsmanagement:saltstack:products:testing) -> [systemsmanagement:saltstack:products](https://build.opensuse.org/project/show/systemsmanagement:saltstack:products)
- [systemsmanagement:saltstack:products:testing:debian](https://build.opensuse.org/project/show/systemsmanagement:saltstack:products:testing:debian) -> [systemsmanagement:saltstack:products:debian](https://build.opensuse.org/project/show/systemsmanagement:saltstack:products:debian)

## Jenkinsfile_promote_salt_bundle_packages

This pipeline takes care of promoting the Salt Bundle package (venv-salt-minion) and its dependencies:

- [systemsmanagement:saltstack:bundle:testing](https://build.opensuse.org/project/show/systemsmanagement:saltstack:bundle:testing) -> [systemsmanagement:saltstack:bundle](https://build.opensuse.org/project/show/systemsmanagement:saltstack:bundle)
- Packages in subprojects
- Project Configs in subprojects

## promote_packages.py

This script is used by the pipelines to take care of the different stages of the promotion.

### Getting started:

```console
# pip3 install -r requirements.txt
# python3 promote_packages.py --help
```
