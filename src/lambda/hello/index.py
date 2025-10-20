import boto3
import json
import unicodedata
import os
import time
import random
import botocore
import logging


bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    transcript = event.get("transcript")
    if not transcript:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Transcript not provided"})
        }
    
    # log the length and first 100 letters of the transcript
    logger.info(f"Received transcript of length {len(transcript)}, excerpt: {json.dumps(transcript)[:100]}")
    
    try:
        # set all return values to blank/defaults
        summary = ""
        takeAways = []
        quotes = []
        tags = {}
        factChecks = {}

        logger.info("Starting summary generation")
        summary = get_summary(transcript)
        logger.info("Summary generation completed: " + json.dumps(summary)[:100])

        logger.info("Starting takeaways extraction")
        # takeAways = get_takeaways(transcript, 5)
        logger.info("Takeaways extraction completed: " + json.dumps(takeAways)[:100])

        logger.info("Starting quotes extraction")
        # quotes = get_quotes(transcript, 2)
        logger.info("Quotes extraction completed: " + json.dumps(quotes)[:100])
        
        logger.info("Starting tags extraction")
        # tags = get_tags(transcript, "tags.json")
        logger.info("Tags extraction completed: " + json.dumps(tags)[:100])
        
        logger.info("Starting fact checking")
        # factChecks = fact_check(transcript)
        logger.info("Fact checking completed: " + json.dumps(factChecks)[:100])

        returnJson = {"summary": summary, 
                    "takeAways": takeAways, 
                    "quotes": quotes,
                    "tags": tags,
                    "factChecks": factChecks}

        return {
            "statusCode": 200,
            "body": json.dumps(returnJson)
        }
    except Exception as e:
        # Log stack trace for debugging and return a 500 to the caller
        logger.error(traceback.format_exc())
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal server error", "message": str(e)})
        }

def get_summary(transcript):
    prompt = f"Summarize the following podcast transcript excerpt in 200-300 words, capturing core themes, key discussions, and outcomes or opinions shared:\n\n{transcript}"
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
    takeaways_json = safe_parse_json(output_text)
    
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
    quotes_json = safe_parse_json(output_text)

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
        "tags": [
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
    tags_json = safe_parse_json(output_text)

    # Validate against allowed list (drop invalids)
    tags_json["tags"] = [tag for tag in tags_json.get("tags", []) if tag in allowed_tags]

    return tags_json


def extract_claims(transcript: str):
    prompt = f"""
        Identify verifiable factual claims in the following transcript. 

        Instructions:
        - Each claim should be concise and self-contained.
        - Do not include opinions, rhetorical questions, or jokes.

        Return ONLY valid JSON:
        {{
        "claims": [
            "Claim 1",
            "Claim 2"
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
    claims_json = safe_parse_json(output_text)
    return claims_json.get("claims", [])


def verify_claim(claim: str):
    prompt = f"""
        You are a fact-checking assistant with access to external sources.

        Verify the following claim:
        "{claim}"


        Instructions:
        - Return ONLY valid JSON.
        - The "verification" field MUST be EXACTLY one of these four strings (copy/paste, do not invent your own):
        - "Verified true"
        - "Possibly outdated/inaccurate"
        - "Unverifiable"
        - Do not add symbols, checkmarks, emojis, or extra words.
        - Include "confidence" as a float between 0.0 and 1.0.

        Output format:
        {{
        "claim": "...",
        "verification": "...",
        "confidence": 0.0
        }}
        """
    response = invoke_model(prompt)
    result = json.loads(response['body'].read())
    output_text = result["content"][0]["text"]
    return json.loads(output_text)


def fact_check(transcript: str):
    claims = extract_claims(transcript)
    verifications = []
    for claim in claims:
        verifications.append(verify_claim(claim))
    return { "facts": verifications }


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


def invoke_model(prompt, retries=5):
    payload = {
        "modelId": "anthropic.claude-3-sonnet-20240229-v1:0",  # or other Claude model IDs
        "accept": "application/json",
        "contentType": "application/json",
        "body": json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "temperature": 0.7,
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": prompt}]}
            ]
        })
    }

    # Invoke the model with retry logic in case we get throttled
    for i in range(retries):
        try:
            response = bedrock.invoke_model(**payload)
            return response
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "ThrottlingException":
                sleep_time = (2 ** i) + random.random()
                logger.warning(f"Throttled on attempt {i+1}/{retries}. Sleeping {sleep_time:.2f}s...")
                time.sleep(sleep_time)
                continue
            else:
                raise
    raise RuntimeError(f"invoke_model failed after {retries} retries due to throttling.")


def safe_parse_json(text: str):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Maybe the model added some extra text, so try recovering a JSON substring
        start = text.find("{")
        end = text.rfind("}") + 1
        try:
            return json.loads(text[start:end])
        except Exception:
            logger.error("LLM returned invalid JSON.  LLM Response: %s", text)
            return {}
