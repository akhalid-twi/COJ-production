#!/bin/bash

while true; do
    echo "Running update_status.sh at $(date)"
    bash update_status.sh
    sleep 7200  # Wait for 2 hour
done

