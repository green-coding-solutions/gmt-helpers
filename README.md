## What is this repo?

The GMT-Helpers repo contains small scripts that help with operating the [Green Metrics Tool](https://github.com/green-coding-solutions/green-metrics-tool/) either 
in a user role or a cluster admin role.

## Guarantees and testing

The scripts in this folder are partially contributed by the community and have no current maintainer or unit-tests to check their validity.

They might be outdated so be sure that they do not come with the same expectations as GMT itself. They **should** work, but also might need some minor tweaks to work in your environment
as they have only been developed in tested in a "works for me" fashion.

## submit_software.py

A little script that enables you to submit jobs to the cluster from the shell. You will need to have `requests` installed. Otherwise run `pip install requests`.

## cron/send_nginx_logs.py

You will need to move this script into the GMT repo and then it can parse the NGINX logs and send you an email.

## Contributing

We love contributions. All scripts in this folder are licensed as MIT and if you contribute you agree to this license.

Note that this license is different from the GMT license itself (AGPLv3)
