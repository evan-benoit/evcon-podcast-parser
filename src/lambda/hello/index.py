import boto3
import json

bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")

def handler(event, context):
    transcript = event.get("transcript")
    if not transcript:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Transcript not provided"})
        }
    
    summary = get_summary(transcript)
    takeAways = get_takeaways(transcript, 5)

    returnJson = {"summary": summary, "takeAways": takeAways}

    return {
        "statusCode": 200,
        "body": json.dumps(returnJson)
    }

def get_summary(transcript):
    prompt = f"Summarize the following podcast transcript excerpt in 200-300 words:\n\n{transcript}"
    response = invoke_model(prompt)
    result = json.loads(response['body'].read())
    output_text = result["content"][0]["text"]
    return output_text

import json


def get_takeaways(transcript, num_takeaways=5):
    prompt = f"""
        You are an assistant that extracts the top {num_takeaways} takeaways from a podcast transcript.

        Instructions:
        - Output ONLY valid JSON.
        - The JSON must be of the form:
        {{
        "takeaways": [
            "Takeaway 1",
            "Takeaway 2",
            ...
        ]
        }}

        Transcript:
        <<<
        {transcript}
        >>>
        """
    response = invoke_model(prompt)
    result = json.loads(response['body'].read())
    output_text = result["content"][0]["text"]

    # Parse Claude’s JSON output safely
    try:
        takeaways_json = json.loads(output_text)
    except json.JSONDecodeError:
        # If Claude adds extra text, try to recover JSON substring
        start = output_text.find("{")
        end = output_text.rfind("}") + 1
        takeaways_json = json.loads(output_text[start:end])

    return takeaways_json["takeaways"]



def invoke_model(prompt):
    response = bedrock.invoke_model(
        modelId='anthropic.claude-3-sonnet-20240229-v1:0',  # or other Claude model IDs
        accept="application/json",
        contentType="application/json",
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "temperature": 0.7,
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": prompt}]}
            ]
        })
    )
    
    return response