#!/usr/bin/env bash
# Usage: ./call_api.sh input.json

API_ENDPOINT="https://wv6a8lyes5.execute-api.us-east-2.amazonaws.com/parse_transcript"

if [ $# -ne 1 ]; then
  echo "Usage: $0 <input-file>"
  exit 1
fi

FILE=$1

if [ ! -f "$FILE" ]; then
  echo "Error: File '$FILE' not found!"
  exit 1
fi

PAYLOAD=$(jq -s '{transcript: .[0]}' "$FILE")

# Debug output
echo "==== Debug: Generated Payload ===="
echo "$PAYLOAD"
echo "================================="


curl -s -X POST "$API_ENDPOINT" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD"

echo