"""
MandiMitra — Multi-Agent Setup Script
Creates 4 specialist sub-agents and configures the existing orchestrator as Supervisor.

Architecture:
  MandiMitra Supervisor (GDSWGCDJIX) [existing]
    ├── PriceIntelligenceAgent  [NEW] — price queries, mandi comparison
    ├── SellAdvisoryAgent       [NEW] — sell/hold decisions
    ├── NegotiationAgent        [NEW] — price briefs for negotiation
    └── WeatherAgent            [NEW] — weather + agri advisory

Usage:
    python create_multi_agent.py

Prerequisites:
    - AWS credentials configured
    - Bedrock Nova Pro model access in us-east-1
    - mandimitra-price-query Lambda ARN available
    - IAM role: MandiMitraBedrockAgentRole
"""
import os
import json
import time
import boto3
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────────────────
REGION = "us-east-1"
ACCOUNT_ID = "471112620976"
PRICE_QUERY_LAMBDA_ARN = f"arn:aws:lambda:{REGION}:{ACCOUNT_ID}:function:mandimitra-price-query"
BEDROCK_AGENT_ROLE_ARN = f"arn:aws:iam::{ACCOUNT_ID}:role/MandiMitraBedrockAgentRole"
MODEL_ID = "amazon.nova-pro-v1:0"
EXISTING_SUPERVISOR_ID = "GDSWGCDJIX"  # existing MandiMitra agent

PROMPT_DIR = os.path.join(os.path.dirname(__file__), "../agent_configs/sub_agents")
# ────────────────────────────────────────────────────────────────────────────

bedrock_agent = boto3.client("bedrock-agent", region_name=REGION)


def read_prompt(filename: str) -> str:
    path = os.path.join(PROMPT_DIR, filename)
    with open(path, encoding="utf-8") as f:
        return f.read()


def wait_for_agent(agent_id: str, target_status: str = "NOT_PREPARED", timeout: int = 60):
    """Poll agent status until it reaches target or timeout."""
    start = time.time()
    while time.time() - start < timeout:
        resp = bedrock_agent.get_agent(agentId=agent_id)
        status = resp["agent"]["agentStatus"]
        if status == target_status or status == "PREPARED":
            return status
        if status in ("FAILED", "DELETING"):
            raise RuntimeError(f"Agent {agent_id} entered {status} state")
        logger.info(f"  Agent {agent_id} status: {status} (waiting...)")
        time.sleep(5)
    raise TimeoutError(f"Agent {agent_id} did not reach {target_status} within {timeout}s")


def create_agent(name: str, description: str, prompt: str) -> str:
    """Create a Bedrock Agent and return its agentId."""
    logger.info(f"Creating agent: {name}")
    resp = bedrock_agent.create_agent(
        agentName=name,
        description=description,
        agentResourceRoleArn=BEDROCK_AGENT_ROLE_ARN,
        foundationModel=MODEL_ID,
        instruction=prompt,
        idleSessionTTLInSeconds=1800,
    )
    agent_id = resp["agent"]["agentId"]
    logger.info(f"  Created {name} with ID: {agent_id}")
    time.sleep(3)
    return agent_id


def add_price_action_group(agent_id: str, group_name: str, functions: list, description: str = ""):
    """Add an action group with functionSchema to a Bedrock agent."""
    logger.info(f"  Adding action group '{group_name}' to agent {agent_id}")
    bedrock_agent.create_agent_action_group(
        agentId=agent_id,
        agentVersion="DRAFT",
        actionGroupName=group_name,
        description=description,
        actionGroupExecutor={"lambda": PRICE_QUERY_LAMBDA_ARN},
        functionSchema={"functions": functions},
    )
    time.sleep(2)


def prepare_agent(agent_id: str):
    logger.info(f"  Preparing agent {agent_id}...")
    bedrock_agent.prepare_agent(agentId=agent_id)
    time.sleep(8)


def publish_agent_version(agent_id: str) -> str:
    """Publish a versioned snapshot from DRAFT (required before creating alias for collaborators)."""
    logger.info(f"  Publishing version for agent {agent_id}...")
    try:
        resp = bedrock_agent.create_agent_version(agentId=agent_id)
        version = resp["agentVersion"]["agentVersion"]
        logger.info(f"  Published version: {version}")
        time.sleep(5)
        return version
    except Exception as e:
        logger.warning(f"  create_agent_version failed: {e} — will try alias without version")
        return "1"


def create_agent_alias(agent_id: str, alias_name: str) -> str:
    # First publish a version (collaborators need a versioned alias, not DRAFT)
    version = publish_agent_version(agent_id)
    logger.info(f"  Creating alias '{alias_name}' for agent {agent_id} → version {version}")
    resp = bedrock_agent.create_agent_alias(
        agentId=agent_id,
        agentAliasName=alias_name,
        routingConfiguration=[{"agentVersion": version}],
    )
    alias_id = resp["agentAlias"]["agentAliasId"]
    logger.info(f"  Alias created: {alias_id}")
    time.sleep(3)
    return alias_id


# ── Function schemas for each specialist agent ───────────────────────────────

PRICE_INTEL_FUNCTIONS = [
    {
        "name": "query_mandi_prices",
        "description": "Query current and historical prices for a commodity from mandis in a state.",
        "parameters": {
            "commodity": {"description": "Commodity name e.g. Soyabean, Wheat, Onion", "type": "string", "required": True},
            "state": {"description": "Indian state name e.g. Madhya Pradesh, Haryana", "type": "string", "required": True},
            "mandi": {"description": "Specific mandi/city name (optional)", "type": "string", "required": False},
            "days": {"description": "Days of history. Default 7.", "type": "integer", "required": False},
        },
    },
    {
        "name": "get_nearby_mandis",
        "description": "Find APMC mandis near GPS coordinates with commodity prices and net realization.",
        "parameters": {
            "latitude": {"description": "User latitude", "type": "number", "required": True},
            "longitude": {"description": "User longitude", "type": "number", "required": True},
            "radius_km": {"description": "Search radius km, default 50", "type": "integer", "required": False},
            "commodity": {"description": "Commodity to get prices for", "type": "string", "required": False},
        },
    },
    {
        "name": "get_price_trend",
        "description": "Get 7-day and 30-day price trend, direction, change%, and volatility.",
        "parameters": {
            "commodity": {"description": "Commodity name", "type": "string", "required": True},
            "state": {"description": "State name", "type": "string", "required": True},
            "mandi": {"description": "Mandi name (optional)", "type": "string", "required": False},
            "days": {"description": "Days of trend. Default 7.", "type": "integer", "required": False},
        },
    },
    {
        "name": "get_msp",
        "description": "Get government Minimum Support Price for a commodity (2025-26 rates).",
        "parameters": {
            "commodity": {"description": "Commodity name", "type": "string", "required": True},
        },
    },
    {
        "name": "calculate_transport_cost",
        "description": "Calculate transport cost from user GPS to a destination mandi.",
        "parameters": {
            "origin_lat": {"description": "Origin latitude", "type": "number", "required": True},
            "origin_lon": {"description": "Origin longitude", "type": "number", "required": True},
            "dest_mandi": {"description": "Destination mandi name", "type": "string", "required": True},
            "quantity_qtl": {"description": "Quantity in quintals", "type": "number", "required": True},
        },
    },
]

SELL_ADVISORY_FUNCTIONS = [
    {
        "name": "get_sell_recommendation",
        "description": "Get comprehensive sell/hold advisory data including prices, trend, shelf life, storage costs, weather risk, and price prediction.",
        "parameters": {
            "commodity": {"description": "Commodity name", "type": "string", "required": True},
            "state": {"description": "State name", "type": "string", "required": True},
            "latitude": {"description": "User latitude", "type": "number", "required": True},
            "longitude": {"description": "User longitude", "type": "number", "required": True},
            "quantity_qtl": {"description": "Quantity in quintals", "type": "number", "required": False},
            "storage_available": {"description": "Whether farmer has storage (true/false)", "type": "string", "required": False},
        },
    },
]

NEGOTIATION_FUNCTIONS = [
    {
        "name": "query_mandi_prices",
        "description": "Query prices from multiple mandis for price brief generation.",
        "parameters": {
            "commodity": {"description": "Commodity name", "type": "string", "required": True},
            "state": {"description": "State name", "type": "string", "required": True},
            "mandi": {"description": "Specific mandi name (optional)", "type": "string", "required": False},
            "days": {"description": "Days of history", "type": "integer", "required": False},
        },
    },
    {
        "name": "get_msp",
        "description": "Get MSP for fair price calculation in price brief.",
        "parameters": {
            "commodity": {"description": "Commodity name", "type": "string", "required": True},
        },
    },
    {
        "name": "get_nearby_mandis",
        "description": "Get prices from nearby mandis for comparison in price brief.",
        "parameters": {
            "latitude": {"description": "User latitude", "type": "number", "required": True},
            "longitude": {"description": "User longitude", "type": "number", "required": True},
            "radius_km": {"description": "Search radius km", "type": "integer", "required": False},
            "commodity": {"description": "Commodity name", "type": "string", "required": False},
        },
    },
    {
        "name": "get_price_trend",
        "description": "Get 7-day trend for price brief.",
        "parameters": {
            "commodity": {"description": "Commodity name", "type": "string", "required": True},
            "state": {"description": "State name", "type": "string", "required": True},
            "mandi": {"description": "Mandi name", "type": "string", "required": False},
            "days": {"description": "Days of trend", "type": "integer", "required": False},
        },
    },
]

WEATHER_FUNCTIONS = [
    {
        "name": "get_weather_advisory",
        "description": "Get 5-day weather forecast and agricultural advisory for a location.",
        "parameters": {
            "location": {"description": "City or mandi name", "type": "string", "required": True},
            "latitude": {"description": "Latitude (if GPS available)", "type": "number", "required": False},
            "longitude": {"description": "Longitude (if GPS available)", "type": "number", "required": False},
        },
    },
]

# ── Main setup flow ───────────────────────────────────────────────────────────

def main():
    results = {}

    # 1. Price Intelligence Agent
    logger.info("\n" + "="*60)
    logger.info("1. Creating Price Intelligence Agent")
    price_agent_id = create_agent(
        "MandiMitra-PriceIntelligence",
        "Specialist for mandi price queries, comparisons, trend analysis, and GPS-based mandi finding",
        read_prompt("price_intelligence_agent_prompt.txt"),
    )
    add_price_action_group(
        price_agent_id, "PriceIntelligenceTools",
        PRICE_INTEL_FUNCTIONS,
        "Tools for price queries, mandi comparison, trend analysis, MSP lookup, transport cost",
    )
    prepare_agent(price_agent_id)
    price_alias_id = create_agent_alias(price_agent_id, "live")
    results["price_intelligence"] = {"agent_id": price_agent_id, "alias_id": price_alias_id}

    # 2. Sell Advisory Agent
    logger.info("\n" + "="*60)
    logger.info("2. Creating Sell Advisory Agent")
    sell_agent_id = create_agent(
        "MandiMitra-SellAdvisory",
        "Specialist for sell/hold/split recommendations based on trend, perishability, storage, weather",
        read_prompt("sell_advisory_agent_prompt.txt"),
    )
    add_price_action_group(
        sell_agent_id, "SellAdvisoryTools",
        SELL_ADVISORY_FUNCTIONS,
        "Comprehensive sell recommendation data with shelf life, storage, weather risk, price prediction",
    )
    prepare_agent(sell_agent_id)
    sell_alias_id = create_agent_alias(sell_agent_id, "live")
    results["sell_advisory"] = {"agent_id": sell_agent_id, "alias_id": sell_alias_id}

    # 3. Negotiation Agent
    logger.info("\n" + "="*60)
    logger.info("3. Creating Negotiation Prep Agent")
    negotiation_agent_id = create_agent(
        "MandiMitra-Negotiation",
        "Generates shareable price briefs for mandi negotiation with traders",
        read_prompt("negotiation_agent_prompt.txt"),
    )
    add_price_action_group(
        negotiation_agent_id, "NegotiationTools",
        NEGOTIATION_FUNCTIONS,
        "Price queries, MSP lookup, and nearby mandi comparison for negotiation briefs",
    )
    prepare_agent(negotiation_agent_id)
    negotiation_alias_id = create_agent_alias(negotiation_agent_id, "live")
    results["negotiation"] = {"agent_id": negotiation_agent_id, "alias_id": negotiation_alias_id}

    # 4. Weather Agent
    logger.info("\n" + "="*60)
    logger.info("4. Creating Weather Advisory Agent")
    weather_agent_id = create_agent(
        "MandiMitra-Weather",
        "5-day weather forecast with agricultural advisory for mandi visits and crop handling",
        read_prompt("weather_agent_prompt.txt"),
    )
    add_price_action_group(
        weather_agent_id, "WeatherTools",
        WEATHER_FUNCTIONS,
        "5-day weather forecast and agricultural advisory via Open-Meteo API",
    )
    prepare_agent(weather_agent_id)
    weather_alias_id = create_agent_alias(weather_agent_id, "live")
    results["weather"] = {"agent_id": weather_agent_id, "alias_id": weather_alias_id}

    # 5. Register sub-agents as collaborators on the Supervisor
    logger.info("\n" + "="*60)
    logger.info("5. Registering sub-agents as collaborators on Supervisor (GDSWGCDJIX)")

    collaborators = [
        {
            "name": "PriceIntelligenceAgent",
            "agent_id": price_agent_id,
            "alias_id": price_alias_id,
            "description": "Call for price queries, mandi comparisons, nearby mandis with GPS, trend analysis",
        },
        {
            "name": "SellAdvisoryAgent",
            "agent_id": sell_agent_id,
            "alias_id": sell_alias_id,
            "description": "Call for sell/hold/split decisions with shelf life, storage, weather risk analysis",
        },
        {
            "name": "NegotiationAgent",
            "agent_id": negotiation_agent_id,
            "alias_id": negotiation_alias_id,
            "description": "Call to generate shareable price briefs for mandi negotiation",
        },
        {
            "name": "WeatherAgent",
            "agent_id": weather_agent_id,
            "alias_id": weather_alias_id,
            "description": "Call for 5-day weather forecasts and agricultural weather guidance",
        },
    ]

    for collab in collaborators:
        try:
            logger.info(f"  Associating {collab['name']}...")
            bedrock_agent.associate_agent_collaborator(
                agentId=EXISTING_SUPERVISOR_ID,
                agentVersion="DRAFT",
                agentDescriptor={
                    "aliasArn": f"arn:aws:bedrock:{REGION}:{ACCOUNT_ID}:agent-alias/{collab['agent_id']}/{collab['alias_id']}"
                },
                collaboratorName=collab["name"],
                collaborationInstruction=collab["description"],
                relayConversationHistory="TO_COLLABORATOR",
            )
            logger.info(f"  ✅ {collab['name']} associated")
            time.sleep(2)
        except Exception as e:
            logger.error(f"  ❌ Failed to associate {collab['name']}: {e}")
            logger.error("  -> You may need to enable agent collaboration in the console and retry")

    # 6. Update supervisor prompt and re-prepare
    logger.info("\n" + "="*60)
    logger.info("6. Updating Supervisor orchestrator prompt")
    new_supervisor_prompt = read_prompt("supervisor_orchestrator_prompt.txt")
    try:
        bedrock_agent.update_agent(
            agentId=EXISTING_SUPERVISOR_ID,
            agentName="MandiMitra",
            agentResourceRoleArn=BEDROCK_AGENT_ROLE_ARN,
            foundationModel=MODEL_ID,
            instruction=new_supervisor_prompt,
            agentCollaboration="SUPERVISOR",  # Enable supervisor mode
        )
        logger.info("  Supervisor prompt updated with SUPERVISOR collaboration mode")
        time.sleep(3)
        prepare_agent(EXISTING_SUPERVISOR_ID)
    except Exception as e:
        logger.error(f"  Failed to update supervisor: {e}")
        logger.error("  -> Update supervisor prompt manually in Bedrock console")

    # Save results
    output_file = os.path.join(os.path.dirname(__file__), "../../multi_agent_ids.json")
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    logger.info("\n" + "="*60)
    logger.info("MULTI-AGENT SETUP COMPLETE")
    logger.info(f"Agent IDs saved to: {output_file}")
    logger.info("\nSub-agent IDs:")
    for name, ids in results.items():
        logger.info(f"  {name}: agentId={ids['agent_id']}, aliasId={ids['alias_id']}")

    logger.info(f"\nSupervisor (existing): {EXISTING_SUPERVISOR_ID} / TSTALIASID")
    logger.info("\nNext steps:")
    logger.info("1. Verify all agents show 'PREPARED' status in AWS Console")
    logger.info("2. Test each sub-agent individually in Bedrock Console")
    logger.info("3. Test the supervisor agent end-to-end")
    logger.info("4. No Lambda changes needed — same mandimitra-chat Lambda works")


if __name__ == "__main__":
    main()
