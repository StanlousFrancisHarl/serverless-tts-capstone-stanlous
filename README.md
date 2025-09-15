# Serverless Text-to-Speech on AWS

**Owner:** Stanlous Francis Haley (Cloud Engineering, Cohort 3 — Azubi Africa)  
**Region:** us-east-1

This project converts text to natural-sounding speech using a **serverless** stack:
- **S3 static website** hosts `index.html`
- **API Gateway (HTTP API)** exposes `POST /speak`
- **AWS Lambda (Python 3.12)** orchestrates the flow
- **Amazon Polly** synthesizes speech (MP3)
- **Private S3 audio bucket** stores MP3s; app uses **pre-signed URLs (~1h)** for playback
- **CloudWatch Logs** capture Lambda execution

---

## Architecture

![Architecture Diagram](architecture/diagram.png)

**Key notes**
- Web bucket is public read (static site).  
- Audio bucket is **private**; 1-day lifecycle expiry; SSE-S3 encryption.  
- CORS configured **only** on API Gateway (Allow: `*` origins, `POST, OPTIONS`, header `content-type`, max-age 3600).  
- Lambda env: `AUDIO_BUCKET`, `URL_TTL_SECONDS=3600`.  
- Lambda IAM: `polly:SynthesizeSpeech`, `s3:PutObject/GetObject` (audio bucket only), and `AWSLambdaBasicExecutionRole`.

---

## Deliverables (in this repo)

- **CloudFormation template:** [`infra/template.yaml`](infra/template.yaml)
- **Architecture diagram:** [`architecture/diagram.png`](architecture/diagram.png)
- **Lambda code:** [`lambda/lambda_function.py`](lambda/lambda_function.py)
- **Project files (web UI):** [`web/index.html`](web/index.html)
- **README:** (this file)

---

## How to deploy with CloudFormation (console, simple)

1. Open **CloudFormation** → **Create stack** → *With new resources (standard)*.  
2. **Template source:** Upload the file from `infra/template.yaml`.  
3. **Parameters:**  
   - **WebBucketName:** a **globally-unique** name (e.g., `tts-web-sfh-2025-09`)  
   - **AudioBucketName:** another unique name (e.g., `tts-audio-sfh-2025-09`)  
   - Leave other defaults unless required.
4. Create the stack (takes a couple of minutes).
5. After it finishes, note the **API Invoke URL** in the **Outputs**.
6. Open your **web bucket** → upload `web/index.html` → (or just copy-paste its content if using the S3 console editor).
7. In `index.html`, set `API_BASE` to the invoke URL (no trailing slash).  
8. Visit the **S3 static website endpoint** shown in the bucket’s *Static website hosting* panel and test.

> **Tip:** You’ve already built everything manually. The template is provided to satisfy the deliverable and for repeatable deploys.

---

## Cost control

- Polly billed per character; test with short strings.
- Audio bucket has a 1-day **lifecycle expire** rule (included in template).
- You can delete the stack to remove all resources created by the template.

---

## Clean up

- If deployed via template: delete the **CloudFormation stack**.  
- If deployed manually: empty and delete both S3 buckets, remove the API, and delete the Lambda.

---

