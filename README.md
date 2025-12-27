# What is this repo?

The GMT-Helpers repo contains small scripts that help with operating the [Green Metrics Tool](https://github.com/green-coding-solutions/green-metrics-tool/) either 
in a user role or a cluster admin role.

## Guarantees and testing

The scripts in this folder are partially contributed by the community and have no current maintainer or unit-tests to check their validity.

They might be outdated so be sure that they do not come with the same expectations as GMT itself. They **should** work, but also might need some minor tweaks to work in your environment
as they have only been developed in tested in a "works for me" fashion.

## Installation

Most scripts can be executed only when the Python venv of the Green Metrics Tool is active.

This means typically a call like this:

`$ /home/user/green-metrics-tool/venv/bin/python3 /home/user/gmt-helpers/nginx/send_log_report.py`

These calls can then be used directly in the `crontab` or your cron manager of choice.

Some other scripts are manually executable like for instance `submit_software.py` and some other must be installed as service. The info is given in the respective info box for the script.

# Scripts

## wake_measurement_machine.py
*Direct Execution*

If you use Wake-on-LAN for your measurement machines to save energy in the cluster you can use this script to start a machine as soon as a job was submitted to the API.

## submit_software.py
*Direct Execution*

A little script that enables you to submit jobs to the cluster from the shell. You will need to have `requests` installed. Otherwise run `pip install requests`.

## nginx/send_log_report.py
*venv Execution*

You need to make the nginx logs from the previous day readable to the script either by copying them out somewhere or changing the `chmod` in place.
Example cronjob if you run nginx outside of the containers as `www-data`: 
```cron
15 0 * * * chmod 644 /var/log/nginx/access.log.1
16 0 * * * chmod 644 /var/log/nginx/error.log.1
```

Example cronjob then for python to run the script: `$ /home/user/green-metrics-tool/venv/bin/python3 /home/user/gmt-helpers/nginx/send_log_report.py`

## db/consistency.py
*venv Execution*

You need to create the following files from the `.example` files:

- `db/queries_check_empty.sql`: Contains queries separated by *\n-------\n* that should result in empty result. Otherwise warning email is sent to configured error email address of GMT.
- `db/queries_info.sql`: Reports result via email from query if no empty result is returned to configured error email address of GMT.

Example cronjob then for python to run the script: `$ /home/user/green-metrics-tool/venv/bin/python3 /home/user/gmt-helpers/db/check_consistency.py`

## wol-webserver
*Service Execution*

If you need to wake a machine from the outside inside your local network you can use this ingress
script to transport a connect to a webserver to WoL command


# Contributing

We love contributions. All scripts in this folder are licensed as MIT and if you contribute you agree to this license.

Note that this license is different from the GMT license itself (AGPLv3)
