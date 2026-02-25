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
            user_message, session_id, language, trace
        )

        elapsed = round(time.time() - start_time, 2)

        # Log to LangFuse
        if trace:
            trace.update(
                output=response_text,
                metadata={"latency_seconds": elapsed, "language": language},
            )
            langfuse.flush()

        return api_response(200, {
            "response": response_text,
            "session_id": session_id,
            "language": language,
            "agent_trace": agent_traces,
            "latency_seconds": elapsed,
        })

    except Exception as e:
        logger.error(f"Agent invocation failed: {str(e)}", exc_info=True)
        if trace:
            trace.update(level="ERROR", status_message=str(e))
            langfuse.flush()
        return api_response(500, {
            "error": "Failed to process your query. Please try again.",
            "detail": str(e),
        })


def invoke_agent(message: str, session_id: str, language: str, trace=None) -> tuple:
    """Invoke Bedrock Agent and collect response + traces."""
    response_parts = []
    agent_traces = []

    # Add language instruction prefix if Hindi
    if language == "hi":
        augmented_message = f"[Respond in Hindi] {message}"
    else:
        augmented_message = message

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
                    text = chunk_data["bytes"].decode("utf-8")
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

    except Exception as e:
        logger.error(f"Bedrock agent invocation error: {e}")
        raise

    full_response = "".join(response_parts)
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
        "body": json.dumps(body, ensure_ascii=False),
    }
