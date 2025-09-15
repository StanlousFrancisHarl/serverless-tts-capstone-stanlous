import json, os, hashlib, boto3, botocore

s3 = boto3.client('s3')
polly = boto3.client('polly')

AUDIO_BUCKET = os.environ.get('AUDIO_BUCKET')
URL_TTL = int(os.environ.get('URL_TTL_SECONDS', '3600'))
DEFAULT_VOICE = os.environ.get('DEFAULT_VOICE_ID', 'Amy')

def _key_for(text, voice):
    h = hashlib.sha1((voice + '|' + text).encode('utf-8')).hexdigest()
    return f"mp3/{voice}/{h}.mp3"

def lambda_handler(event, context):
    try:
        body = event.get('body')
        if isinstance(body, str):
            body = json.loads(body or "{}")

        text = (body or {}).get('text', '').strip()
        voice = (body or {}).get('voiceId') or DEFAULT_VOICE
        if not text:
            return _resp(400, {"error": "Missing 'text'"})

        key = _key_for(text, voice)

        # Cache hit?
        exists = False
        try:
            s3.head_object(Bucket=AUDIO_BUCKET, Key=key)
            exists = True
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] != '404':
                raise

        if not exists:
            # Call Polly and save MP3
            ss = polly.synthesize_speech(Text=text, VoiceId=voice, OutputFormat='mp3')
            audio = ss['AudioStream'].read()
            s3.put_object(Bucket=AUDIO_BUCKET, Key=key, Body=audio, ContentType='audio/mpeg')

        url = s3.generate_presigned_url(
            ClientMethod='get_object',
            Params={'Bucket': AUDIO_BUCKET, 'Key': key},
            ExpiresIn=URL_TTL
        )
        return _resp(200, {"url": url, "key": key, "cached": exists})

    except Exception as e:
        return _resp(500, {"error": str(e)})

def _resp(code, body):
    return {
        "statusCode": code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(body)
    }
