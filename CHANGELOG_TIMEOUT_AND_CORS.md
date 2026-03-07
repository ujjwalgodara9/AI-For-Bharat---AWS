# Changelog: API Gateway Timeout Fix, CORS, and Encoding Fix

This document records all changes made to fix chat timeouts, CORS (OPTIONS), and Lambda logging encoding issues for MandiMitra.

---

## 1. Problem Summary

- **Chat** was intermittently failing with **504 / timeout**.
- **OPTIONS** (CORS preflight) to the Lambda Function URL returned **400 Bad Request**.
- After fixing CORS, chat could still fail when the Bedrock response contained **emoji/Unicode** due to a **charmap encoding error** in Lambda logging.

---

## 2. Root Causes

| Issue | Cause |
|-------|--------|
| **29s timeout** | API Gateway REST API has a **hard 29-second** integration timeout. Bedrock multi-agent often takes 15–30+ seconds. |
| **OPTIONS 400** | Chat Lambda did not handle **OPTIONS**; it always tried to parse the body as JSON, so preflight failed. |
| **charmap error** | `logger.info(..., preview: repr(full_response[:80]))` could include emoji (e.g. 🙏). In some environments this triggered `'charmap' codec can't encode character` and broke the request. |

---

## 3. Changes Made

### 3.1 Point frontend chat to Lambda Function URL (bypass API Gateway)

**Files:**

- **`frontend/.env.local`**
  - Added:
    ```env
    NEXT_PUBLIC_CHAT_URL=https://qkatltxwdichmmb7t5oqj23jg40xhuae.lambda-url.us-east-1.on.aws/
    ```

- **`frontend/app/page.tsx`**
  - Added constant:
    ```ts
    const CHAT_URL = process.env.NEXT_PUBLIC_CHAT_URL || `${API_BASE}/chat`;
    ```
  - Changed the **chat** `fetch` from `fetch(\`${API_BASE}/chat\`, ...)` to `fetch(CHAT_URL, ...)`.
  - **Unchanged:** All other calls (prices, crop list) still use `API_BASE` (API Gateway).

**Effect:** Chat requests go directly to the Lambda Function URL, so the 29s API Gateway limit no longer applies (Lambda timeout is 60s; Function URL supports up to 15 minutes).

---

### 3.2 Handle OPTIONS (CORS preflight) in the chat Lambda

**File:** `backend/lambdas/chat_handler/handler.py`

**Change:** At the start of `handler(event, context)`:

- Read HTTP method from `event["requestContext"]["http"]["method"]` (Lambda Function URL) or `event.get("httpMethod")`.
- If `method == "OPTIONS"`, return immediately with:
  - `statusCode: 200`
  - Headers: `Access-Control-Allow-Origin: *`, `Access-Control-Allow-Headers: Content-Type,Authorization`, `Access-Control-Allow-Methods: POST,OPTIONS`
  - `body: ""`
- Only parse the body and run chat logic for non-OPTIONS (e.g. POST).

**Effect:** Browser CORS preflight succeeds; the actual POST is then sent and processed.

---

### 3.3 Safe logging to avoid Unicode/emoji encoding errors

**File:** `backend/lambdas/chat_handler/handler.py`

**Change:**

- Added helper:
  ```python
  def _safe_log_preview(text: str, max_len: int = 80) -> str:
      """ASCII-safe preview for logging (avoids charmap/Unicode errors in some environments)."""
      if not text:
          return ""
      preview = (text[:max_len] + "..." if len(text) > max_len else text)
      return preview.encode("ascii", errors="replace").decode("ascii")
  ```
- Replaced log lines that included raw response preview with `_safe_log_preview(...)`:
  - `logger.info(f"Full response length: ..., preview: {_safe_log_preview(full_response)}")`
  - `logger.warning(f"Response looks like internal reasoning ({_safe_log_preview(full_response, 60)}), ...")`
  - `logger.warning(f"Response too short ({_safe_log_preview(full_response, 60)}), ...")`

**Effect:** Logging no longer raises `'charmap' codec can't encode character` when the Bedrock response contains emoji or other non-ASCII characters.

---

## 4. What was not changed

- **`backend/lambdas/chat_handler/handler.py`** — No change to retry/fallback logic (already fixed earlier; no second Bedrock call on empty response).
- **Prices / other API calls** — Still use API Gateway base URL (`NEXT_PUBLIC_API_URL`).
- **Lambda timeout** — Already set to 60s for `mandimitra-chat` (done earlier).
- **Lambda Function URL** — Already created with NONE auth; URL unchanged.

---

## 5. Deploy steps (for reference)

### Frontend (after .env and page.tsx changes)

```bash
cd frontend
npm run build
aws s3 sync out/ s3://mandimitra-frontend-471112620976/ --delete --region us-east-1
aws cloudfront create-invalidation --distribution-id E1FOPZ17Q7P6CF --paths "/*" --region us-east-1
```

(On Windows, use `aws.cmd` if `aws` is not in PATH.)

### Chat Lambda (after handler.py changes)

1. From `backend/lambdas/chat_handler`: install deps and create zip:
   ```powershell
   pip install -r requirements.txt -t .
   $items = Get-ChildItem | Where-Object { $_.Name -ne '__pycache__' -and $_.Name -ne 'requirements.txt' }
   Compress-Archive -Path $items.FullName -DestinationPath "..\chat_handler.zip" -Force
   ```
2. Update Lambda:
   ```bash
   aws lambda update-function-code --function-name mandimitra-chat --zip-file "fileb://path/to/chat_handler.zip" --region us-east-1
   ```

---

## 6. Verification

- **OPTIONS:** In DevTools → Network, the preflight to the Lambda Function URL returns **200** with CORS headers.
- **POST:** Chat request goes to `...lambda-url.us-east-1.on.aws/` and returns **200** even when the response takes 25–35 seconds.
- **Logs:** In CloudWatch (`/aws/lambda/mandimitra-chat`), no `charmap` encoding errors when the model returns emoji.

---

## 7. Summary table

| Item | Before | After |
|------|--------|--------|
| Chat request URL | API Gateway `/prod/api/chat` | Lambda Function URL (same host as OPTIONS) |
| Max wait for chat response | 29s (API Gateway) | 60s (Lambda; Function URL allows longer) |
| OPTIONS to Function URL | 400 (body parse error) | 200 + CORS headers |
| Logging response preview | `repr(full_response[:80])` (could raise charmap) | `_safe_log_preview(full_response)` |
