import boto3
import json


def handler(event, context):

    bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")

    transcript = event.get("transcript", "No transcript provided.")
    prompt = f"Summarize the following podcast transcript excerpt:\n\n{transcript}"

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

    result = json.loads(response['body'].read())
    output_text = result["content"][0]["text"]

    return {
        "statusCode": 200,
        "body": json.dumps({"summary": output_text})
    }