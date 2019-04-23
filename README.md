# Linux_Server_configuration-ud_FSND
Ubuntu 16.04 configuration serving item-catalog project(ud-FSND-part4): Udacity FSND part5 capstone project

Find the app at: alebisiani.io (111.111.111.111)


ssh at: 48373


## Index
1. Summary of software and configuration
1. Third party- resources used for config


## Summary of software and configuration
#### Software
* Hosted on DigitalOcean
* nginx
* Python 3.7
* pip
* pipenv

#### Configuration
* root remote login disabled
* administrator's user and grader user configured with root privileges
* password login disabled
* ssh hosted on non-standard port

* nginx listening on port 80


## Third party- resources used for config
* DigitalOcean tutorials:
- https://www.digitalocean.com/docs/droplets/how-to/connect-with-ssh/
- https://www.digitalocean.com/community/tutorials/initial-server-setup-with-ubuntu-16-04


* THING
* https://www.digitalocean.com/community/tutorials/how-to-serve-flask-applications-with-uwsgi-and-nginx-on-ubuntu-16-04