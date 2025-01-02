#!/bin/bash

# Get the current date
current_date=$(date +"%Y-%m-%d")

# Calculate the number of seconds until 18:00
end_time=$(date -d "18:00" +%s)
current_time=$(date +%s)
seconds_until_end=$((end_time - current_time))

while [ $SECONDS -lt $seconds_until_end ]; do
    tail -n 30 logs/trade_strategies_$current_date.log
    sleep 120  # Wait for 2 minutes
done

# Make the script executable
# chmod +x print_logs.sh
