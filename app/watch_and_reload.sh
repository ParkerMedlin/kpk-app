#!/bin/sh

PORT=$1

echo "Starting watch_and_reload.sh script on port $PORT"

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
    daphne -b 0.0.0.0 -p $PORT app.asgi:application 2>&1 | filter_daphne_output &
    DAPHNE_PID=$! # This is the PID of the filter_daphne_output subshell
    echo "Daphne (filter PID: $DAPHNE_PID) started."
}

stop_daphne() {
    echo "DEBUG: stop_daphne called for filter PID: '${DAPHNE_PID}'"
    if [ -n "$DAPHNE_PID" ] && ps -p "$DAPHNE_PID" > /dev/null 2>&1; then
        echo "Stopping Daphne (targeting filter PID: $DAPHNE_PID and its process group)..."
        
        # Get the Process Group ID (PGID) of the filter process
        FILTER_PGID=$(ps -o pgid= -p "$DAPHNE_PID" | tr -d ' ')
        
        if [ -n "$FILTER_PGID" ]; then
            echo "DEBUG: Attempting to kill process group $FILTER_PGID..."
            kill -TERM "-$FILTER_PGID" 2>/dev/null || echo "DEBUG: Failed to kill process group -$FILTER_PGID. Trying individual PID $DAPHNE_PID."
        fi
        
        # Fallback or direct kill if PGID kill wasn't sufficient or PGID not found
        if ps -p "$DAPHNE_PID" > /dev/null 2>&1; then # Check if filter still exists
             kill -TERM "$DAPHNE_PID" 2>/dev/null || echo "DEBUG: Failed to kill filter PID $DAPHNE_PID directly."
        fi

        echo "DEBUG: Waiting for filter PID $DAPHNE_PID to terminate..."
        wait "$DAPHNE_PID" 2>/dev/null || echo "DEBUG: Wait for filter PID $DAPHNE_PID returned non-zero (process might be already gone or unwaitable)."
        
        echo "Daphne processes presumed stopped."
    else
        echo "DEBUG: No active DAPHNE_PID ($DAPHNE_PID) to stop or process already gone."
    fi
    DAPHNE_PID=""
    echo "DEBUG: stop_daphne finished."
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
        echo "DEBUG: stop_daphne returned. Calling start_daphne."
        start_daphne
        echo "DEBUG: start_daphne returned."
        mv $TEMP_CHECKSUM_FILE $CHECKSUM_FILE
        echo "Checksums updated"
    else
        rm $TEMP_CHECKSUM_FILE
    fi
    sleep 2
done

# please make sure this is in LF