#!/bin/bash

while true; do
    echo "Running update_status.sh at $(date)"
    bash update_status.sh
    sleep 3600  # Wait for 1 hour
done

