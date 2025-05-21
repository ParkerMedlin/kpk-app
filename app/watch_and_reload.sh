#!/bin/sh

PORT=$1

echo "Starting watch_and_reload.sh script on port $PORT"

start_daphne() {
    echo "Starting Daphne on port $PORT"
    daphne -b 0.0.0.0 -p $PORT app.asgi:application 2>&1 | grep -v 'GET /core/api/get-single-tank-level/' &
    DAPHNE_PID=$!
    echo "Daphne started with PID $DAPHNE_PID"
}

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
        kill $DAPHNE_PID
        wait $DAPHNE_PID 2>/dev/null
        start_daphne
        mv $TEMP_CHECKSUM_FILE $CHECKSUM_FILE
        echo "Checksums updated"
    else
        rm $TEMP_CHECKSUM_FILE
    fi
    sleep 2
done

# please make sure this is in LF