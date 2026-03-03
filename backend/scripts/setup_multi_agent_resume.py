"""
MandiMitra — Multi-Agent Setup (Resume)
Resumes from where create_multi_agent.py left off.
PriceIntelligence agent CAEJ90IYS6 already exists.
"""
import os, json, time, boto3, logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

REGION = "us-east-1"
ACCOUNT_ID = "471112620976"
PRICE_QUERY_LAMBDA_ARN = f"arn:aws:lambda:{REGION}:{ACCOUNT_ID}:function:mandimitra-price-query"
BEDROCK_AGENT_ROLE_ARN = f"arn:aws:iam::{ACCOUNT_ID}:role/MandiMitraBedrockAgentRole"
MODEL_ID = "amazon.nova-pro-v1:0"
SUPERVISOR_ID = "GDSWGCDJIX"
PROMPT_DIR = os.path.join(os.path.dirname(__file__), "../agent_configs/sub_agents")

client = boto3.client("bedrock-agent", region_name=REGION)


def rp(filename):
    with open(os.path.join(PROMPT_DIR, filename), encoding="utf-8") as f:
        return f.read()


def make_agent(name, description, prompt):
    logger.info(f"Creating {name}...")
    resp = client.create_agent(
        agentName=name, description=description,
        agentResourceRoleArn=BEDROCK_AGENT_ROLE_ARN,
        foundationModel=MODEL_ID, instruction=prompt,
        idleSessionTTLInSeconds=1800,
    )
    aid = resp["agent"]["agentId"]
    logger.info(f"  {name} = {aid}")
    time.sleep(3)
    return aid


def add_ag(agent_id, group_name, functions, description=""):
    logger.info(f"  Adding {group_name} to {agent_id}...")
    client.create_agent_action_group(
        agentId=agent_id, agentVersion="DRAFT",
        actionGroupName=group_name, description=description,
        actionGroupExecutor={"lambda": PRICE_QUERY_LAMBDA_ARN},
        functionSchema={"functions": functions},
    )
    time.sleep(2)


def publish_and_alias(agent_id, alias_name, existing_alias_id=None):
    """Prepare agent and create a versioned alias.
    If existing_alias_id is provided, skip alias creation (already done)."""
    logger.info(f"  Preparing {agent_id}...")
    client.prepare_agent(agentId=agent_id)
    time.sleep(10)
    if existing_alias_id:
        logger.info(f"  Using existing alias: {existing_alias_id}")
        return existing_alias_id
    logger.info(f"  Creating alias '{alias_name}' (server auto-versions DRAFT)...")
    # Do NOT pass routingConfiguration — server creates a snapshot version automatically
    resp = client.create_agent_alias(
        agentId=agent_id, agentAliasName=alias_name,
        description=f"Production alias for {alias_name}",
    )
    alias_id = resp["agentAlias"]["agentAliasId"]
    logger.info(f"  Alias: {alias_id} (status: {resp['agentAlias']['agentAliasStatus']})")
    time.sleep(8)  # wait for CREATING → PREPARED
    return alias_id


# --- Function schemas ---
PRICE_FUNCTIONS = [
    {"name": "query_mandi_prices", "description": "Query current and historical prices for a commodity from mandis in a state.", "parameters": {"commodity": {"description": "Commodity e.g. Soyabean, Wheat", "type": "string", "required": True}, "state": {"description": "Indian state e.g. Madhya Pradesh", "type": "string", "required": True}, "mandi": {"description": "Specific mandi name (optional)", "type": "string", "required": False}, "days": {"description": "Days of history, default 7", "type": "integer", "required": False}}},
    {"name": "get_nearby_mandis", "description": "Find APMC mandis near GPS coordinates with commodity prices.", "parameters": {"latitude": {"description": "User latitude", "type": "number", "required": True}, "longitude": {"description": "User longitude", "type": "number", "required": True}, "radius_km": {"description": "Search radius km, default 50", "type": "integer", "required": False}, "commodity": {"description": "Commodity to price", "type": "string", "required": False}}},
    {"name": "get_price_trend", "description": "Get 7-day/30-day price trend, direction, change%, volatility.", "parameters": {"commodity": {"description": "Commodity name", "type": "string", "required": True}, "state": {"description": "State name", "type": "string", "required": True}, "mandi": {"description": "Mandi name (optional)", "type": "string", "required": False}, "days": {"description": "Days of trend", "type": "integer", "required": False}}},
    {"name": "get_msp", "description": "Get government Minimum Support Price for a commodity.", "parameters": {"commodity": {"description": "Commodity name", "type": "string", "required": True}}},
    {"name": "calculate_transport_cost", "description": "Calculate transport cost from GPS to a mandi.", "parameters": {"origin_lat": {"description": "Origin latitude", "type": "number", "required": True}, "origin_lon": {"description": "Origin longitude", "type": "number", "required": True}, "dest_mandi": {"description": "Destination mandi name", "type": "string", "required": True}, "quantity_qtl": {"description": "Quantity in quintals", "type": "number", "required": True}}},
]

SELL_FUNCTIONS = [
    {"name": "get_sell_recommendation", "description": "Get comprehensive sell/hold advisory data including prices, trend, shelf life, storage costs, weather risk, and price prediction.", "parameters": {"commodity": {"description": "Commodity name", "type": "string", "required": True}, "state": {"description": "State name", "type": "string", "required": True}, "latitude": {"description": "User latitude", "type": "number", "required": True}, "longitude": {"description": "User longitude", "type": "number", "required": True}, "quantity_qtl": {"description": "Quantity in quintals", "type": "number", "required": False}}},
]

NEGO_FUNCTIONS = [
    {"name": "query_mandi_prices", "description": "Query prices from multiple mandis for price brief.", "parameters": {"commodity": {"description": "Commodity name", "type": "string", "required": True}, "state": {"description": "State name", "type": "string", "required": True}, "mandi": {"description": "Mandi name (optional)", "type": "string", "required": False}, "days": {"description": "Days of history", "type": "integer", "required": False}}},
    {"name": "get_msp", "description": "Get MSP for fair price calculation.", "parameters": {"commodity": {"description": "Commodity name", "type": "string", "required": True}}},
    {"name": "get_nearby_mandis", "description": "Get prices from nearby mandis for comparison.", "parameters": {"latitude": {"description": "User latitude", "type": "number", "required": True}, "longitude": {"description": "User longitude", "type": "number", "required": True}, "radius_km": {"description": "Search radius km", "type": "integer", "required": False}, "commodity": {"description": "Commodity name", "type": "string", "required": False}}},
    {"name": "get_price_trend", "description": "Get trend for price brief.", "parameters": {"commodity": {"description": "Commodity name", "type": "string", "required": True}, "state": {"description": "State name", "type": "string", "required": True}, "mandi": {"description": "Mandi name", "type": "string", "required": False}, "days": {"description": "Days of trend", "type": "integer", "required": False}}},
]

WEATHER_FUNCTIONS = [
    {"name": "get_weather_advisory", "description": "Get 5-day weather forecast and agricultural advisory.", "parameters": {"location": {"description": "City or mandi name", "type": "string", "required": True}, "latitude": {"description": "Latitude (optional)", "type": "number", "required": False}, "longitude": {"description": "Longitude (optional)", "type": "number", "required": False}}},
]


def main():
    results = {}

    # Step 1 — Price Intelligence (already created with alias 7YU2OMSRBQ)
    price_agent_id = "CAEJ90IYS6"
    price_alias_id = "7YU2OMSRBQ"
    logger.info(f"\n{'='*60}")
    logger.info(f"1. Price Intelligence: {price_agent_id} / alias {price_alias_id} (pre-existing, skipping)")
    results["price_intelligence"] = {"agent_id": price_agent_id, "alias_id": price_alias_id}

    # Step 2 — Sell Advisory (agent CCYSN80MGN already created)
    logger.info(f"\n{'='*60}")
    logger.info("2. Sell Advisory Agent already created (CCYSN80MGN), adding action group...")
    sell_id = "CCYSN80MGN"
    add_ag(sell_id, "SellAdvisoryTools", SELL_FUNCTIONS, "Comprehensive sell advisory with shelf life, storage, weather risk")
    sell_alias_id = publish_and_alias(sell_id, "live")
    results["sell_advisory"] = {"agent_id": sell_id, "alias_id": sell_alias_id}

    # Step 3 — Negotiation
    logger.info(f"\n{'='*60}")
    logger.info("3. Creating Negotiation Agent...")
    nego_id = make_agent("MandiMitra-Negotiation", "Shareable price briefs for mandi negotiation with traders", rp("negotiation_agent_prompt.txt"))
    add_ag(nego_id, "NegotiationTools", NEGO_FUNCTIONS, "Price queries and nearby mandi comparison for negotiation briefs")
    nego_alias_id = publish_and_alias(nego_id, "live")
    results["negotiation"] = {"agent_id": nego_id, "alias_id": nego_alias_id}

    # Step 4 — Weather
    logger.info(f"\n{'='*60}")
    logger.info("4. Creating Weather Agent...")
    weather_id = make_agent("MandiMitra-Weather", "5-day weather forecast with agri advisory for mandi visits", rp("weather_agent_prompt.txt"))
    add_ag(weather_id, "WeatherTools", WEATHER_FUNCTIONS, "5-day forecast and agricultural advisory via Open-Meteo")
    weather_alias_id = publish_and_alias(weather_id, "live")
    results["weather"] = {"agent_id": weather_id, "alias_id": weather_alias_id}

    # Step 5 — Associate collaborators on Supervisor
    logger.info(f"\n{'='*60}")
    logger.info("5. Associating sub-agents as Supervisor collaborators...")
    collaborators = [
        ("PriceIntelligenceAgent", price_agent_id, price_alias_id, "Call for price queries, mandi comparisons, nearby mandis, trend analysis"),
        ("SellAdvisoryAgent", sell_id, sell_alias_id, "Call for sell/hold/split decisions with shelf life, storage, weather risk"),
        ("NegotiationAgent", nego_id, nego_alias_id, "Call to generate shareable price briefs for mandi negotiation"),
        ("WeatherAgent", weather_id, weather_alias_id, "Call for 5-day weather forecasts and agricultural advisory"),
    ]
    for cname, caid, calid, cdesc in collaborators:
        try:
            client.associate_agent_collaborator(
                agentId=SUPERVISOR_ID, agentVersion="DRAFT",
                agentDescriptor={"aliasArn": f"arn:aws:bedrock:{REGION}:{ACCOUNT_ID}:agent-alias/{caid}/{calid}"},
                collaboratorName=cname, collaborationInstruction=cdesc,
                relayConversationHistory="TO_COLLABORATOR",
            )
            logger.info(f"  ✅ {cname} ({caid}/{calid}) associated")
            time.sleep(2)
        except Exception as e:
            logger.error(f"  ❌ {cname}: {e}")

    # Step 6 — Update supervisor to SUPERVISOR mode
    logger.info(f"\n{'='*60}")
    logger.info("6. Updating Supervisor to SUPERVISOR collaboration mode...")
    try:
        from pathlib import Path
        supervisor_prompt = rp("supervisor_orchestrator_prompt.txt")
        client.update_agent(
            agentId=SUPERVISOR_ID,
            agentName="MandiMitra",
            agentResourceRoleArn=BEDROCK_AGENT_ROLE_ARN,
            foundationModel=MODEL_ID,
            instruction=supervisor_prompt,
            agentCollaboration="SUPERVISOR",
        )
        logger.info("  ✅ Supervisor updated with SUPERVISOR collaboration mode")
        time.sleep(3)
        client.prepare_agent(agentId=SUPERVISOR_ID)
        logger.info("  ✅ Supervisor re-prepared")
        time.sleep(10)
    except Exception as e:
        logger.error(f"  ❌ Supervisor update failed: {e}")
        logger.warning("  → Update manually in console: set agentCollaboration=SUPERVISOR")

    # Save results
    output_path = os.path.join(os.path.dirname(__file__), "../../multi_agent_ids.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    logger.info(f"\n{'='*60}")
    logger.info("DONE. Summary:")
    for name, ids in results.items():
        logger.info(f"  {name}: {ids['agent_id']} / {ids['alias_id']}")
    logger.info(f"\nSupervisor: {SUPERVISOR_ID} / TSTALIASID (no Lambda change needed)")
    logger.info(f"Results saved to: {output_path}")


if __name__ == "__main__":
    main()
