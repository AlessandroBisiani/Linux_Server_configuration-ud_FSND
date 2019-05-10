# Linux Server Configuration - Udacity FSND
#### Udacity FSND part 5 capstone project: Ubuntu 16.04 configuration serving item-catalog project(ud-FSND-part4)
<br>

Find the app at: alebisiani.io (104.248.43.26)

ssh at: 2200
<br>
<br>


## Index
1. Summary of software and configuration
1. Third-party resources used for configuration


## Summary of software and configuration
#### Software
* Hosted on DigitalOcean
* apache 2
* Python 3.7
* pip
* virtualenv
* For the item-catalog: flask, sqlalchemy, httplib2, requests, oauth2client, requests, python-dotenv


#### Configuration
* root remote login disabled
* Administrator's user and grader user configured with root privileges
* Password login disabled
* ssh hosted on 2200
* Port 80 proxied to local 8080 where flask is hosted


## Third-party resources used for configuration
* DigitalOcean tutorials:
- https://www.digitalocean.com/docs/droplets/how-to/connect-with-ssh/
- https://www.digitalocean.com/community/tutorials/initial-server-setup-with-ubuntu-16-04
- https://www.digitalocean.com/community/tutorials/how-to-use-apache-as-a-reverse-proxy-with-mod_proxy-on-ubuntu-16-04
