#!/bin/bash
# Usage: ./invoke.sh samples/my-test.json

if [ -z "$1" ]; then
  echo "Usage: $0 <path-to-file>"
  exit 1
fi

FILE=$1
OUT=response.json

aws lambda invoke \
  --function-name rmind-hello \
  --cli-binary-format raw-in-base64-out \
  --payload "$(jq -Rs '{transcript:.}' "$FILE")" \
  $OUT

echo "---- Lambda response ----"
cat $OUT | jq .