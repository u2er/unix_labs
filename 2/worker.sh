#!/bin/sh

DATA_DIR="/data"
LOCK_FILE="$DATA_DIR/sync.lock"
MAX_FILES=999

MY_ID=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 8 | head -n 1)
SEQ=1

mkdir -p "$DATA_DIR"

exec 200>"$LOCK_FILE"

echo "Container $MY_ID started."

while true; do
    flock -x 200

    i=1
    FOUND=0
    while [ "$i" -le "$MAX_FILES" ]; do
        FNAME=$(printf "%03d" "$i")
        FPATH="$DATA_DIR/$FNAME"

        if [ ! -e "$FPATH" ]; then
            echo "$MY_ID $SEQ" > "$FPATH"
            FOUND=1
            break
        fi
        i=$((i+1))
    done

    flock -u 200

    if [ "$FOUND" -eq 0 ]; then
        sleep 1
        continue
    fi

    sleep 1
    rm -f "$FPATH"
    SEQ=$((SEQ+1))
done
