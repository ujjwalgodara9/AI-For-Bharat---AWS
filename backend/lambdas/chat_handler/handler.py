"""
MandiMitra — Chat Handler Lambda
Receives user messages, invokes Bedrock Agent, returns response with trace.
Includes LangFuse tracing for observability.
"""
import os
import json
import time
import uuid
import logging
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients
bedrock_agent_runtime = boto3.client(
    "bedrock-agent-runtime",
    region_name=os.environ.get("AWS_REGION", "us-east-1")
)

# Configuration
AGENT_ID = os.environ.get("BEDROCK_AGENT_ID", "")
AGENT_ALIAS_ID = os.environ.get("BEDROCK_AGENT_ALIAS_ID", "")

# LangFuse (optional, degrades gracefully)
langfuse = None
try:
    from langfuse import Langfuse
    lf_public = os.environ.get("LANGFUSE_PUBLIC_KEY")
    lf_secret = os.environ.get("LANGFUSE_SECRET_KEY")
    lf_host = os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com")
    if lf_public and lf_secret:
        langfuse = Langfuse(public_key=lf_public, secret_key=lf_secret, host=lf_host)
        logger.info("LangFuse tracing enabled")
except ImportError:
    logger.info("LangFuse not installed, tracing disabled")


def handler(event, context):
    """Main Lambda handler for chat endpoint."""
    start_time = time.time()

    # Parse request
    try:
        if isinstance(event.get("body"), str):
            body = json.loads(event["body"])
        else:
            body = event.get("body", event)
    except (json.JSONDecodeError, TypeError):
        return api_response(400, {"error": "Invalid JSON body"})

    user_message = body.get("message", "").strip()
    language = body.get("language", "hi")  # Default to Hindi
    session_id = body.get("session_id", str(uuid.uuid4()))
    user_lat = body.get("latitude")
    user_lon = body.get("longitude")

    if not user_message:
        return api_response(400, {"error": "Message is required"})

    # Start LangFuse trace
    trace = None
    if langfuse:
        trace = langfuse.trace(
            name="mandimitra-chat",
            session_id=session_id,
            input=user_message,
            metadata={"language": language},
        )

    try:
        # Invoke Bedrock Agent
        response_text, agent_traces = invoke_agent(
            user_message, session_id, language, trace,
            user_lat=user_lat, user_lon=user_lon,
        )

        elapsed = round(time.time() - start_time, 2)

        # Log to LangFuse
        if trace:
            trace.update(
                output=response_text,
                metadata={"latency_seconds": elapsed, "language": language},
            )
            langfuse.flush()

        result_body = {
            "response": response_text,
            "session_id": session_id,
            "language": language,
            "agent_trace": agent_traces,
            "latency_seconds": elapsed,
        }
        logger.info(f"Result body response field length: {len(result_body['response'])}")
        body_str = json.dumps(result_body, ensure_ascii=True)
        logger.info(f"JSON body length: {len(body_str)}")
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json; charset=utf-8",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,Authorization",
                "Access-Control-Allow-Methods": "POST,OPTIONS",
            },
            "body": body_str,
        }

    except Exception as e:
        logger.error(f"Agent invocation failed: {str(e)}", exc_info=True)
        if trace:
            trace.update(level="ERROR", status_message=str(e))
            langfuse.flush()
        return api_response(500, {
            "error": "Failed to process your query. Please try again.",
            "detail": str(e),
        })


def invoke_agent(message: str, session_id: str, language: str, trace=None,
                  user_lat=None, user_lon=None) -> tuple:
    """Invoke Bedrock Agent and collect response + traces."""
    response_parts = []
    answer_from_trace = []
    agent_traces = []

    # Build augmented message with language and location context
    parts = []
    if language == "hi":
        parts.append("[Respond in Hindi]")
    if user_lat is not None and user_lon is not None:
        parts.append(f"[User GPS location: latitude={user_lat}, longitude={user_lon}. Use this for nearby mandi lookups and transport cost calculations.]")
    parts.append(message)
    augmented_message = " ".join(parts)

    try:
        response = bedrock_agent_runtime.invoke_agent(
            agentId=AGENT_ID,
            agentAliasId=AGENT_ALIAS_ID,
            sessionId=session_id,
            inputText=augmented_message,
            enableTrace=True,
        )

        # Process the streaming response
        event_stream = response.get("completion", [])
        for event in event_stream:
            # Collect response text chunks
            if "chunk" in event:
                chunk_data = event["chunk"]
                if "bytes" in chunk_data:
                    raw_bytes = chunk_data["bytes"]
                    if raw_bytes:
                        text = raw_bytes.decode("utf-8") if isinstance(raw_bytes, bytes) else str(raw_bytes)
                        response_parts.append(text)

            # Collect agent trace information
            if "trace" in event:
                trace_data = event["trace"].get("trace", {})
                trace_entry = extract_trace(trace_data)
                if trace_entry:
                    agent_traces.append(trace_entry)

                    # Log each step to LangFuse
                    if trace and langfuse:
                        span = trace.span(
                            name=trace_entry.get("type", "agent_step"),
                            input=trace_entry.get("input"),
                            output=trace_entry.get("output"),
                            metadata=trace_entry.get("metadata", {}),
                        )

                # Also try to extract answer from model invocation output
                orch = trace_data.get("orchestrationTrace", {})
                if "modelInvocationOutput" in orch:
                    mio = orch["modelInvocationOutput"]
                    raw = mio.get("rawResponse", {}).get("content", "")
                    raw_str = str(raw)
                    if "<answer>" in raw_str:
                        try:
                            # The content may be nested JSON — try to extract text field first
                            text_to_search = raw_str
                            try:
                                parsed = json.loads(raw_str) if isinstance(raw, str) else raw
                                if isinstance(parsed, dict):
                                    texts = parsed.get("output", {}).get("message", {}).get("content", [])
                                    if texts:
                                        text_to_search = texts[0].get("text", raw_str)
                            except (json.JSONDecodeError, TypeError, KeyError, IndexError):
                                pass

                            if "<answer>" in text_to_search:
                                start = text_to_search.index("<answer>") + len("<answer>")
                                end = text_to_search.index("</answer>") if "</answer>" in text_to_search else len(text_to_search)
                                answer = text_to_search[start:end].strip()
                                if answer and len(answer) > 5:
                                    answer_from_trace.append(answer)
                                    logger.info(f"Extracted answer from trace: {len(answer)} chars")
                        except Exception as ex:
                            logger.warning(f"Answer extraction error: {ex}")

    except Exception as e:
        logger.error(f"Bedrock agent invocation error: {e}")
        raise

    logger.info(f"Response parts count: {len(response_parts)}, sizes: {[len(p) for p in response_parts]}")
    full_response = "".join(response_parts)
    logger.info(f"Full response length: {len(full_response)}, preview: {repr(full_response[:80])}")

    # Strip "Bot:" or "Bot: " prefix injected by Bedrock multi-agent framework
    if full_response.startswith("Bot:"):
        full_response = full_response[4:].lstrip(" \n").strip()
        logger.info(f"Stripped 'Bot:' prefix. New length: {len(full_response)}")

    # Detect leaked internal reasoning — Bedrock sometimes streams only the thinking prefix
    # e.g. "Thought:", "I need to", "(1)" — these are not valid user-facing responses
    INTERNAL_PREFIXES = ("Thought:", "I need to", "(1)", "(2)", "The user", "The User")
    is_internal_reasoning = bool(full_response) and any(
        full_response.startswith(p) for p in INTERNAL_PREFIXES
    )
    if is_internal_reasoning:
        logger.warning(f"Response looks like internal reasoning ({repr(full_response[:60])}), will try trace fallback")
        full_response = ""

    # Also treat suspiciously short responses (< 10 chars) as empty so trace fallback can help
    if full_response and len(full_response) < 10:
        logger.warning(f"Response too short ({repr(full_response)}), will try trace fallback")
        full_response = ""

    # Fallback 1: if chunk bytes were empty OR contained leaked reasoning,
    # use the answer extracted from <answer> tags in the model invocation traces
    if not full_response and answer_from_trace:
        full_response = answer_from_trace[-1]  # Use the last (final) answer
        logger.info(f"Using answer from trace fallback: {len(full_response)} chars")

    # Fallback 2: retry WITHOUT traces (sometimes enableTrace causes empty chunks)
    if not full_response:
        logger.info("Response empty after trace fallback, retrying without traces...")
        try:
            retry_response = bedrock_agent_runtime.invoke_agent(
                agentId=AGENT_ID,
                agentAliasId=AGENT_ALIAS_ID,
                sessionId=session_id + "-retry",
                inputText=augmented_message,
                enableTrace=False,
            )
            retry_parts = []
            for event in retry_response.get("completion", []):
                if "chunk" in event and "bytes" in event["chunk"]:
                    raw_bytes = event["chunk"]["bytes"]
                    if raw_bytes:
                        retry_parts.append(raw_bytes.decode("utf-8") if isinstance(raw_bytes, bytes) else str(raw_bytes))
            if retry_parts:
                full_response = "".join(retry_parts)
                logger.info(f"Retry without traces succeeded: {len(full_response)} chars")
        except Exception as retry_err:
            logger.error(f"Retry failed: {retry_err}")

    return full_response, agent_traces


def extract_trace(trace_data: dict) -> dict:
    """Extract readable trace info from Bedrock agent trace event."""
    trace_entry = {}

    # Orchestration trace (intent classification, agent routing)
    if "orchestrationTrace" in trace_data:
        orch = trace_data["orchestrationTrace"]

        if "rationale" in orch:
            trace_entry = {
                "type": "reasoning",
                "step": "Agent Reasoning",
                "output": orch["rationale"].get("text", ""),
            }

        if "invocationInput" in orch:
            inv = orch["invocationInput"]
            trace_entry = {
                "type": "tool_call",
                "step": "Tool Invocation",
                "input": {
                    "action_group": inv.get("actionGroupInvocationInput", {}).get("actionGroupName", ""),
                    "function": inv.get("actionGroupInvocationInput", {}).get("function", ""),
                    "parameters": inv.get("actionGroupInvocationInput", {}).get("parameters", []),
                },
            }

        if "observation" in orch:
            obs = orch["observation"]
            trace_entry = {
                "type": "observation",
                "step": "Tool Result",
                "output": obs.get("actionGroupInvocationOutput", {}).get("text", ""),
            }

        if "modelInvocationOutput" in orch:
            mio = orch["modelInvocationOutput"]
            raw_content = mio.get("rawResponse", {}).get("content", "")
            if raw_content and "<answer>" in str(raw_content):
                trace_entry = {
                    "type": "model_output",
                    "step": "Model Response",
                    "output": str(raw_content),
                }

        if "modelInvocationInput" in orch:
            model_input = orch["modelInvocationInput"]
            trace_entry["metadata"] = {
                "model": model_input.get("inferenceConfiguration", {}).get("modelId", ""),
            }

    # Pre-processing trace
    if "preProcessingTrace" in trace_data:
        pre = trace_data["preProcessingTrace"]
        if "modelInvocationOutput" in pre:
            output = pre["modelInvocationOutput"]
            trace_entry = {
                "type": "preprocessing",
                "step": "Intent Classification",
                "output": output.get("parsedResponse", {}).get("rationale", ""),
            }

    return trace_entry if trace_entry else None


def api_response(status_code: int, body: dict) -> dict:
    """Format Lambda response for API Gateway."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "POST,OPTIONS",
        },
        "body": json.dumps(body, ensure_ascii=True),
    }
