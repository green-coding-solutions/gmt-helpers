#!/bin/bash

MACHINE_ID=1
MACHINE_MAC_ADDRESS='90:80:bb:aa:8d:33'
AUTHENTICATION_TOKEN='xxxxxxxx'
LOCAL_NETWORK_SUBMASK='192.168.178.255'
API_HOST='api.green-coding.io'


# Run your command and capture the output
output=$(curl "https://${API_HOST}/v2/jobs?machine_id=${MACHINE_ID}&state=WAITING" -H 'X-Authentication: ${AUTHENTICATION_TOKEN}' --silent  |  jq '.["data"] | length')

# Check if the output is a specific string
if [[ "$output" =~ ^[0-9]+$ && $output -ne 0 ]]; then
    echo "Having waiting jobs. Starting another program..."

    wakeonlan -i $LOCAL_NETWORK_SUBMASK -p 1234 $MACHINE_MAC_ADDRESS

    # Replace the following line with the command to start the other program
    # For example: /path/to/your/other_program
    echo "Other program started!"
else
    echo "Command output is '0'. No other program started."
fi
