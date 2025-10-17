import index
import json
import sys
from index import handler

def main():
    if len(sys.argv) < 2:
        print("Usage: python test.py <path-to-transcript-file>")
        sys.exit(1)

    file_path = sys.argv[1]

    # Load your test transcript file
    with open(file_path, "r") as f:
        transcript_data = json.load(f)

    # Create a fake Lambda event with transcript
    event = {
        "transcript": transcript_data
    }

    # context can be None for local testing
    result = handler(event, None)

    # Pretty print the response
    print("Lambda result:")
    print(json.dumps(json.loads(result["body"]), indent=2))

if __name__ == "__main__":
    main()