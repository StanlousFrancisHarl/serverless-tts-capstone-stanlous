import json, os, hashlib
import boto3
import botocore

s3 = boto3.client('s3')
polly = boto3.client('polly')

BUCKET = os.environ['AUDIO_BUCKET']
URL_TTL = int(os.environ.get('URL_TTL_SECONDS', '3600'))

def _resp(status, body):
    return { 
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(body)
    }

def lambda_handler(event, context):
    """
    Accepts:
      - direct invoke with dict: {"text": "...", "voiceId": "Amy", "pitch":"1", "speed":"1"}
      - API Gateway proxy with string body: {"body": "{\"text\":\"...\",\"voiceId\":\"Amy\"}"}
    Returns: {"url": "<presigned S3 URL>", "key": "<s3 key>", "cached": bool, "chars": int}
    """
    try:
        body = event.get("body") if isinstance(event, dict) else None
        if isinstance(body, str):
            body = json.loads(body)
        elif body is None and isinstance(event, dict):
            body = event  # allow direct Lambda test

        text = (body.get("text") or "").strip()
        voice = (body.get("voiceId") or "Amy").strip()
        pitch = str(body.get("pitch", "1")).strip()
        speed = str(body.get("speed", "1")).strip()

        if not text:
            return _resp(400, {"error": "Missing 'text'."})
        if len(text) > 1500:
            return _resp(400, {"error": "Text too long. Keep under ~1500 characters."})

        # Stable S3 key so repeats are cached
        key = f"mp3/{voice}/{hashlib.sha256((voice + '|' + text + pitch + speed).encode('utf-8')).hexdigest()}.mp3"

        # If already exists, just return a URL
        try:
            s3.head_object(Bucket=BUCKET, Key=key)
            url = s3.generate_presigned_url("get_object",
                                            Params={"Bucket": BUCKET, "Key": key},
                                            ExpiresIn=URL_TTL)
            return _resp(200, {"url": url, "key": key, "cached": True, "chars": len(text)})
        except botocore.exceptions.ClientError as e:
            if e.response.get("Error", {}).get("Code") not in ("404", "NoSuchKey", "NotFound"):
                raise  # real error; rethrow

        # Build SSML with pitch/speed
        ssml_text = f'<speak><prosody rate="{float(speed)*100:.0f}%" pitch="{float(pitch)*100:.0f}%">{text}</prosody></speak>'

        # Synthesize with Polly (Standard engine for Free Tier)
        polly_resp = polly.synthesize_speech(
            Engine="standard",
            OutputFormat="mp3",
            VoiceId=voice,
            TextType="ssml",
            Text=ssml_text
        )
        audio_bytes = polly_resp["AudioStream"].read()

        s3.put_object(
            Bucket=BUCKET,
            Key=key,
            Body=audio_bytes,
            ContentType="audio/mpeg"
        )

        url = s3.generate_presigned_url("get_object",
                                        Params={"Bucket": BUCKET, "Key": key},
                                        ExpiresIn=URL_TTL)
        return _resp(200, {"url": url, "key": key, "cached": False, "chars": len(text)})

    except Exception as e:
        return _resp(500, {"error": str(e)})
