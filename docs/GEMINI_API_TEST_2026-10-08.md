# Gemini API diagnostic - 8 October 2026

A user-requested fixed synthetic connectivity test verified generation on
[Gemini 3.1 Flash-Lite](https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite).
The saved model and fallback produced different outcomes:

| Model | HTTP | Result | Request duration |
|---|---:|---|---:|
| gemini-3.5-flash-lite (saved configuration) | 503 | Generation unverified | 8.610 seconds |
| gemini-3.1-flash-lite (explicit fallback test) | 200 | Exact GEMINI_API_OK response; finish reason STOP | 1.297 seconds |

The successful response reported **22 prompt tokens, 6 output tokens, 28 total
tokens**. The failed response reported no usage. Dollar cost remains unknown.
See the [sanitized measurements](evaluation/GEMINI_API_TEST_2026-10-08.json).

The successful request started at **23:31:52 IST** on 8 October. There were two
requests in total, each with a 256-output-token limit, no automatic retries and
a durable pre-request marker. The second request followed the user's earlier
instruction to test a lighter model after generation failure. Historical
benchmark ledgers were not used, reset or overwritten.

The test used the ignored local API key in Google's authentication header.
Only a fixed synthetic test message was sent; no research, documents or tracing
payloads were sent. Sanitized results omit credentials and raw provider error
messages. The saved model configuration and public fixture deployment were not
changed by these diagnostics.

This verifies basic API generation for one successful model/request. It does not
verify the structured EvidenceForge workflow, broader research quality, current
reliability of gemini-3.5-flash-lite or whether the provider billed either request.
Hosting remains free only (INR 0/month).
