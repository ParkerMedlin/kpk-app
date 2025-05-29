#!/bin/sh

PORT=$1

# echo "Starting watch_and_reload.sh script on port $PORT"

# Global state for Daphne's filter PID and its Process Group ID
DAPHNE_FILTER_PID=""
DAPHNE_PGID="" # Process Group ID of the pipeline (daphne | filter)

# Function to filter Daphne's output
filter_daphne_output() {
    while IFS= read -r line; do
        if ! echo "$line" | grep -q 'GET /core/api/get-single-tank-level/'; then
            echo "$line"
        fi
    done
}

start_daphne() {
    echo "Starting Daphne on port $PORT"
    # Start daphne piped to filter, run in background
    daphne -b 0.0.0.0 -p $PORT app.asgi:application 2>&1 | filter_daphne_output &
    
    DAPHNE_FILTER_PID=$! # PID of the filter_daphne_output process SHEEEEEEEIIT
    
    # Attempt to get the PGID of the filter process immediately.
    # This PGID should be shared by the daphne process in the same pipeline.
    if ps -p "$DAPHNE_FILTER_PID" > /dev/null 2>&1; then
        DAPHNE_PGID=$(ps -o pgid= -p "$DAPHNE_FILTER_PID" | tr -d ' ')
        # echo "Daphne service started. Filter PID: $DAPHNE_FILTER_PID, Process Group ID for termination: $DAPHNE_PGID"
    else
        # echo "WARN: Daphne\'s filter process (PID $DAPHNE_FILTER_PID) exited very quickly. Could not reliably get its PGID."
        # echo "WARN: Subsequent stops might rely solely on port-based killing if PGID is not available."
        DAPHNE_PGID="" # Ensure it's cleared if not found
    fi
}

stop_daphne() {
    # echo "DEBUG: stop_daphne called. Target Filter PID: '${DAPHNE_FILTER_PID}', Target PGID: '${DAPHNE_PGID}', Port: $PORT"
    local daphne_likely_stopped=false

    # Attempt 1: Kill process group using the stored DAPHNE_PGID
    if [ -n "$DAPHNE_PGID" ]; then
        # echo "DEBUG: Attempting to kill process group -$DAPHNE_PGID..."
        if kill -TERM "-$DAPHNE_PGID" 2>/dev/null; then
            # echo "DEBUG: SIGTERM sent to process group -$DAPHNE_PGID."
            daphne_likely_stopped=true
            sleep 1 # Give a moment for group kill to take effect
        fi
    else
        echo "DEBUG: No DAPHNE_PGID stored. Skipping process group kill. This might happen if filter died too fast at start."
    fi

    # Attempt 2: Clean up the filter process specifically if it's still around
    if [ -n "$DAPHNE_FILTER_PID" ]; then # If a filter PID was recorded
        if ps -p "$DAPHNE_FILTER_PID" > /dev/null 2>&1; then
            # echo "DEBUG: Filter process $DAPHNE_FILTER_PID still seems to exist. Sending SIGTERM directly."
            kill -TERM "$DAPHNE_FILTER_PID" 2>/dev/null
        fi
    fi
    
    # Attempt 3: Fallback/Verification - robustly find and kill whatever is on the port
    # echo "DEBUG: Performing fallback/verification kill for processes on port $PORT."
    PIDS_ON_PORT_OUTPUT=$(fuser $PORT/tcp 2>/dev/null)
    
    if [ -n "$PIDS_ON_PORT_OUTPUT" ]; then
        # echo "DEBUG: Found PIDs on port $PORT: '$PIDS_ON_PORT_OUTPUT'. Attempting SIGTERM."
        for pid_on_port in $PIDS_ON_PORT_OUTPUT; do
            if kill -0 "$pid_on_port" 2>/dev/null; then 
                # echo "DEBUG: Sending SIGTERM to PID $pid_on_port on port $PORT."
                if kill -TERM "$pid_on_port" 2>/dev/null; then
                    daphne_likely_stopped=true
                fi
            fi
        done

        sleep 1 # Give a moment for SIGTERM to work

        PIDS_STILL_ON_PORT_OUTPUT=$(fuser $PORT/tcp 2>/dev/null)
        if [ -n "$PIDS_STILL_ON_PORT_OUTPUT" ]; then
            # echo "DEBUG: PIDs still on port $PORT after SIGTERM: '$PIDS_STILL_ON_PORT_OUTPUT'. Attempting SIGKILL."
            for pid_to_kill in $PIDS_STILL_ON_PORT_OUTPUT; do
                if kill -0 "$pid_to_kill" 2>/dev/null; then
                    # echo "DEBUG: Sending SIGKILL to PID $pid_to_kill."
                    kill -KILL "$pid_to_kill" 2>/dev/null
                    daphne_likely_stopped=true
                fi
            done
        else
            # echo "DEBUG: Processes on port $PORT terminated after SIGTERM."
            daphne_likely_stopped=true 
        fi
    fi

    # Clear global PIDs for the next run
    DAPHNE_FILTER_PID=""
    DAPHNE_PGID="" 
    # echo "DEBUG: stop_daphne finished."
}

# Ensure we clean up on script exit
trap stop_daphne EXIT HUP INT QUIT TERM

start_daphne

echo "Starting file watch loop"
CHECKSUM_FILE="/tmp/checksums.md5"
mkdir -p /tmp
find /app -name "*.py" -type f -print0 | xargs -0 md5sum > $CHECKSUM_FILE
echo "Initial checksums created"

while true; do
    TEMP_CHECKSUM_FILE="/tmp/temp_checksums.md5"
    find /app -name "*.py" -type f -print0 | xargs -0 md5sum > $TEMP_CHECKSUM_FILE

    if ! cmp -s $CHECKSUM_FILE $TEMP_CHECKSUM_FILE; then
        echo "Python file changed. Restarting Daphne..."
        stop_daphne
        start_daphne
        mv $TEMP_CHECKSUM_FILE $CHECKSUM_FILE
        echo "Checksums updated"
    else
        rm $TEMP_CHECKSUM_FILE
    fi
    sleep 2
done

# please make sure this is in LF