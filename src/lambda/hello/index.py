import boto3
import json
import unicodedata
import os


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
    quotes = get_quotes(transcript, 2)
    tags = get_tags(transcript, "tags.json")

    returnJson = {"summary": summary, 
                  "takeAways": takeAways, 
                  "quotes": quotes,
                  "tags": tags}

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

def get_takeaways(transcript, num=5):
    prompt = f"""
        You are an assistant that extracts the top {num} takeaways from a podcast transcript.

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
    
    # Validate that we have the correct number of takeaways
    if len(takeaways_json.get("takeaways", [])) != num:
        return []

    return takeaways_json["takeaways"]


def get_quotes(transcript, num=5):
    prompt = f"""
       Extract notable quotes from the following podcast transcript.

        Instructions:
        - Return ONLY valid JSON.
        - Each quote must be verbatim from the transcript.
        - Each quote must include:
        - "timestamp" (the time code, if available in the transcript)
        - "text" (the exact verbatim quote)
        - Return {num} notable quotes, no commentary.

            Return ONLY valid JSON in this format:
            {{
            "quotes": [
                {{
                "timestamp": "00:12:34",
                "speaker": "Guest",
                "text": "Remote work isn’t just a perk anymore — it’s the new baseline expectation."
                }}
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
        quotes_json = json.loads(output_text)
    except json.JSONDecodeError:
        # If Claude adds extra text, try to recover JSON substring
        start = output_text.find("{")
        end = output_text.rfind("}") + 1
        quotes_json = json.loads(output_text[start:end])

    # Validate quotes are verbatim.  If they are not, return empty list.
    # if not validate_quotes(transcript, quotes_json):
        # return []

    # Validate that we have the correct number of quotes
    if len(quotes_json.get("quotes", [])) != num:
        return []

    return quotes_json["quotes"]

import json

def get_tags(transcript: str, tags_file="tags.json"):
    # Load allowed tags
    tags_path = os.path.join(os.path.dirname(__file__), tags_file)
    with open(tags_path, "r") as f:
        tags_data = json.load(f)
    allowed_tags = tags_data.get("tags", [])

    # Build prompt
    prompt = f"""
        You are tagging a podcast transcript.

        Instructions:
        - Select the most relevant tags from the provided list.
        - Only use tags from the list. Do not invent new tags.
        - Return ONLY valid JSON in this format:
        {{
        "topics": [
            "Tag1",
            "Tag2",
            "Tag3"
        ]
        }}

        Available tags:
        {allowed_tags}

        Transcript:
        <<<
        {transcript}
        >>>
        """

    # Call LLM
    response = invoke_model(prompt)
    result = json.loads(response['body'].read())
    output_text = result["content"][0]["text"]

    # Parse JSON
    tags_json = json.loads(output_text)

    # Validate against allowed list
    for tag in tags_json.get("topics", []):
        if tag not in allowed_tags:
            raise ValueError(f"Invalid tag returned: {tag}")

    return tags_json



def normalize(s: str) -> str:
    # Convert to NFKC form and replace smart quotes/apostrophes
    s = unicodedata.normalize("NFKC", s)
    return s.replace("’", "'").replace("“", '"').replace("”", '"')


def validate_quotes(transcript: str, quotes_json: dict) -> bool:
    norm_transcript = normalize(transcript)
    for quote in quotes_json.get("quotes", []):
        text = normalize(quote.get("text", ""))
        if text not in norm_transcript:
            #If it fails, fall back to an LLM check that can say “close enough.”
            return False
    return True


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