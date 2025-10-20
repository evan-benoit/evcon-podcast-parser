import boto3
import json
import unicodedata
import os
import time
import random
import botocore
import logging
import re
import traceback
from jsonschema import validate, ValidationError

# Define the expected schema for the transcript input
transcript_schema = {
    "type": "object",
    "properties": {
        "episode_id": {"type": "string"},
        "title": {"type": "string"},
        "host": {"type": "string"},
        "guests": {
            "type": "array",
            "items": {"type": "string"}
        },
        "transcript": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "timestamp": {"type": "string"},
                    "speaker": {"type": "string"},
                    "section": {"type": "string"},
                    "text": {"type": "string"}
                },
                "required": ["timestamp", "speaker", "text"]
            }
        }
    },
    "required": ["episode_id", "title", "host", "guests", "transcript"]
}

# Define verification result constants
VERIFICATION_RESULT = ["Verified true", "Possibly outdated/inaccurate", "Unverifiable"]

# set up some libraries
bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# this is the main entry point for the lambda
def handler(event, context):
    transcript = event.get("transcript")
    if not transcript:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Transcript not provided"})
        }
    
    # Validate transcript schema
    is_valid, error_msg = validate_transcript(transcript)
    if not is_valid:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Invalid transcript format", "message": error_msg})
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
        # summary = get_summary(transcript)
        logger.info("Summary generation completed: " + json.dumps(summary)[:100])

        logger.info("Starting takeaways extraction")
        # takeAways = get_takeaways(transcript, 5)
        logger.info("Takeaways extraction completed: " + json.dumps(takeAways)[:100])

        logger.info("Starting quotes extraction")
        quotes = get_quotes(transcript, 2)
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

def validate_transcript(data):
    try:
        validate(instance=data, schema=transcript_schema)
        return True, None
    except ValidationError as e:
        return False, str(e)


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
        - Each quote should be verbatim from the transcript, except you may remove filler words and fix transcription errors
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
    quotes = []

    # Confirm that each quote is in the transcript, and not hallucinated
    for quote in quotes_json.get("quotes", []):
        
        #first we'll do a simple substring check, since it's faster
        if normalize(quote.get("text", "")) not in normalize(json.dumps(transcript)):

            # next, try calling an LLM to verify the quote
            verify_prompt = f"""
            Does the following quote appear in the transcript below?
            Quote: "{quote.get("text")}"
            Transcript:
            <<<
            {json.dumps(transcript, ensure_ascii=False)}
            >>>
            Answer "Yes" or "No" only.
            """
            verify_response = invoke_model(verify_prompt)
            verify_result = json.loads(verify_response['body'].read())
            verify_output_text = verify_result["content"][0]["text"].strip().lower()
            if "yes" not in verify_output_text:
                logger.error(f"Quote not verified by LLM: {quote.get('text')}")
                continue  # skip this quote

        # If we reach here, the quote is valid
        quotes.append(quote)


    return quotes_json["quotes"]

# helper function to normalize strings for comparison
def normalize(s: str) -> str:
    if not s:
        return ""
    return re.sub(r'[^a-z0-9]', '', s.lower())


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
        - The "verification" field MUST be EXACTLY one of these strings (copy/paste, do not invent your own):
             {VERIFICATION_RESULT}
        
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
        logger.info(f"Fact-checking claim: {claim}")
        verification = verify_claim(claim)

        # make sure the verification field has one of the expected values
        valid_verifications = VERIFICATION_RESULT
        if verification.get("verification") not in valid_verifications:
            logger.error(f"Invalid verification result for claim '{claim}': {verification.get('verification')}")
            #skip this claim
            continue

        #make sure the verification has confidence between 0.0 and 1.0
        confidence = verification.get("confidence", -1.0)
        if not isinstance(confidence, (float, int)) or not (0.0 <= confidence <= 1.0):
            logger.error(f"Invalid confidence value for claim '{claim}': {confidence}")
            #skip this claim
            continue

        verifications.append(verification)
        logger.info(f"Verification result: {verifications[-1]}")
    return { "facts": verifications }


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


# helper to safely parse JSON, with some recovery attempts
def safe_parse_json(text: str):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Maybe the model added some extra text, so try recovering a JSON substring
        start = text.find("{")
        end = text.rfind("}") + 1
        try:
            return json.loads(text[start:end])
        
        #The LLM returned garbage we can’t salvage
        except Exception:
            logger.error("If You Don't Like My Output, Blame Your Prompting Skills.  LLM Response: %s", text)
            return {}
