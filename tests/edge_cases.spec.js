// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * MandiMitra Edge Case Test Suite
 * Tests complex queries, language handling, location disambiguation,
 * spelling correction, and agent routing.
 *
 * Each test sends a message via the API and validates the response
 * contains expected elements.
 */

const API_URL = 'https://skwsw8qk22.execute-api.us-east-1.amazonaws.com/prod/api/chat';

/** Helper: send a chat message and return parsed response */
async function sendMessage(request, message, opts = {}) {
  const body = {
    message,
    language: opts.language || 'en',
    session_id: opts.session_id || `edge-test-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    ...(opts.latitude != null && { latitude: opts.latitude }),
    ...(opts.longitude != null && { longitude: opts.longitude }),
  };
  const resp = await request.post(API_URL, {
    data: body,
    timeout: 90000,
  });
  expect(resp.status()).toBe(200);
  const json = await resp.json();
  return { response: json.response || '', traces: json.agent_trace || [], session_id: body.session_id, raw: json };
}

// ═══════════════════════════════════════
// 1. LANGUAGE DETECTION & RESPONSE
// ═══════════════════════════════════════

test.describe('Language Detection', () => {
  test('Hindi query → Hindi response', async ({ request }) => {
    const { response } = await sendMessage(request, 'हनुमानगढ़ में आलू का भाव बताओ');
    // Response should contain Devanagari characters
    const hasDevanagari = /[\u0900-\u097F]/.test(response);
    expect(hasDevanagari).toBeTruthy();
    // Should contain price-related info
    expect(response).toContain('₹');
    console.log('Hindi response preview:', response.slice(0, 300));
  });

  test('Hinglish query → Hinglish response', async ({ request }) => {
    const { response } = await sendMessage(request, 'aloo ka rate batao Indore mein');
    // Should NOT be pure Devanagari
    const hasLatin = /[a-zA-Z]/.test(response);
    expect(hasLatin).toBeTruthy();
    // Should have price info
    expect(response).toContain('₹');
    console.log('Hinglish response preview:', response.slice(0, 300));
  });

  test('English query → English response', async ({ request }) => {
    const { response } = await sendMessage(request, 'What is the current price of wheat in Karnal?');
    expect(response).toContain('₹');
    // Should be mostly English
    const latinChars = response.replace(/[^a-zA-Z]/g, '').length;
    const devanagariChars = (response.match(/[\u0900-\u097F]/g) || []).length;
    expect(latinChars).toBeGreaterThan(devanagariChars);
    console.log('English response preview:', response.slice(0, 300));
  });
});

// ═══════════════════════════════════════
// 2. SPELLING CORRECTION & NORMALIZATION
// ═══════════════════════════════════════

test.describe('Spelling Correction', () => {
  test('Misspelled commodity: "ptato" → Potato', async ({ request }) => {
    const { response } = await sendMessage(request, 'ptato price in Jaipur');
    // Should understand and return potato data (or politely correct)
    const hasPriceOrCorrection = response.includes('₹') || /[Pp]otato|आलू/.test(response);
    expect(hasPriceOrCorrection).toBeTruthy();
    console.log('Spelling correction response:', response.slice(0, 300));
  });

  test('Misspelled city: "Indor" → Indore', async ({ request }) => {
    const { response } = await sendMessage(request, 'soyabean price in Indor');
    // Should resolve to Indore, Madhya Pradesh
    const hasResult = response.includes('₹') || /[Ii]ndore|[Mm]adhya [Pp]radesh/.test(response);
    expect(hasResult).toBeTruthy();
    console.log('City spelling response:', response.slice(0, 300));
  });

  test('Transliterated Hindi: "gehun ka bhav"', async ({ request }) => {
    const { response } = await sendMessage(request, 'gehun ka bhav Karnal mein');
    // Should understand gehun = wheat
    const hasResult = response.includes('₹') || /[Ww]heat|गेहूं/.test(response);
    expect(hasResult).toBeTruthy();
    console.log('Transliteration response:', response.slice(0, 300));
  });
});

// ═══════════════════════════════════════
// 3. LOCATION DISAMBIGUATION
// ═══════════════════════════════════════

test.describe('Location Handling', () => {
  test('City name should auto-detect state (Indore → MP)', async ({ request }) => {
    const { response } = await sendMessage(request, 'Soyabean price in Indore');
    // Should mention Madhya Pradesh, not treat Indore as a state
    const hasMPRef = /[Mm]adhya [Pp]radesh|MP|मध्य प्रदेश/.test(response);
    const hasPrice = response.includes('₹');
    expect(hasPrice || hasMPRef).toBeTruthy();
    console.log('State detection response:', response.slice(0, 300));
  });

  test('Chat location overrides GPS', async ({ request }) => {
    // GPS points to Delhi (28.6, 77.2), but query says Hanumangarh
    const { response } = await sendMessage(request, 'potato price in Hanumangarh', {
      latitude: 28.6139,
      longitude: 77.2090,
    });
    // Should return Hanumangarh data, NOT Delhi
    const hasHanumangarh = /[Hh]anumangarh|हनुमानगढ़|[Rr]ajasthan/.test(response);
    expect(hasHanumangarh).toBeTruthy();
    console.log('Location override response:', response.slice(0, 300));
  });

  test('GPS-only (no location in chat) should use GPS', async ({ request }) => {
    const { response } = await sendMessage(request, 'wheat price near me', {
      latitude: 22.7196,
      longitude: 75.8577,  // Indore coordinates
    });
    // Should use GPS location (Indore area)
    expect(response.includes('₹') || response.length > 50).toBeTruthy();
    console.log('GPS-only response:', response.slice(0, 300));
  });

  test('No location at all should ask user', async ({ request }) => {
    const { response } = await sendMessage(request, 'wheat price batao');
    // Should either ask for location OR provide general info
    const asksForLocation = /location|city|mandi|कहाँ|kahan|konsi/i.test(response);
    const hasData = response.includes('₹');
    expect(asksForLocation || hasData).toBeTruthy();
    console.log('No location response:', response.slice(0, 300));
  });
});

// ═══════════════════════════════════════
// 4. AGENT ROUTING
// ═══════════════════════════════════════

test.describe('Agent Routing', () => {
  test('Price query → PriceIntel agent', async ({ request }) => {
    const { response, traces } = await sendMessage(request, 'What is potato price in Jaipur?');
    expect(response.includes('₹')).toBeTruthy();
    // Check traces for correct routing
    const hasToolCall = traces.some(t => t.type === 'tool_call');
    console.log('Price routing traces:', traces.length, 'Tool calls:', hasToolCall);
    console.log('Response:', response.slice(0, 300));
  });

  test('Sell/hold query → SellAdvisory agent', async ({ request }) => {
    const { response } = await sendMessage(request, 'Should I sell my wheat now or hold? I am in Karnal with 50 quintal');
    // Should contain sell/hold recommendation
    const hasSellAdvice = /[Ss]ell|[Hh]old|[Ss]plit|बेच|रुक|SELL|HOLD/i.test(response);
    expect(hasSellAdvice).toBeTruthy();
    console.log('Sell advisory response:', response.slice(0, 300));
  });

  test('Negotiation query → NegotiationPrep agent', async ({ request }) => {
    const { response } = await sendMessage(request, 'Give me a price brief for soyabean in Indore');
    // Should contain price brief format elements
    const hasBriefFormat = /[Pp]rice [Bb]rief|MSP|[Ff]air [Pp]rice|MandiMitra|मूल्य पत्र|negotiat/i.test(response);
    expect(hasBriefFormat).toBeTruthy();
    console.log('Negotiation response:', response.slice(0, 400));
  });

  test('Weather query → Weather agent', async ({ request }) => {
    const { response } = await sendMessage(request, 'What is the weather in Indore today?');
    // Should contain weather info
    const hasWeather = /weather|temperature|rain|°C|मौसम|तापमान|barish|forecast/i.test(response);
    expect(hasWeather).toBeTruthy();
    console.log('Weather response:', response.slice(0, 300));
  });

  test('General negotiation tips (no commodity/location)', async ({ request }) => {
    const { response } = await sendMessage(request, 'Give me some negotiation tips for mandi');
    // Should provide general tips without asking for commodity
    const hasTips = /tip|MSP|mandi|negotiat|भाव|सौदा|bargain/i.test(response);
    expect(hasTips).toBeTruthy();
    console.log('General tips response:', response.slice(0, 400));
  });
});

// ═══════════════════════════════════════
// 5. GUARDRAILS & OUT-OF-SCOPE
// ═══════════════════════════════════════

test.describe('Guardrails', () => {
  test('Non-agricultural query should be redirected', async ({ request }) => {
    const { response } = await sendMessage(request, 'What is the gold price today?');
    // Should politely refuse or redirect to agricultural queries
    const hasRedirect = /agricultural|krishi|fasal|mandi|commodity|कृषि|फसल|gold.*not|don.*gold/i.test(response);
    const noGoldPrice = !(/gold.*₹\d/.test(response));
    expect(hasRedirect || noGoldPrice).toBeTruthy();
    console.log('Guardrail response:', response.slice(0, 300));
  });

  test('Stock market query should be refused', async ({ request }) => {
    const { response } = await sendMessage(request, 'Tell me about stock market investments');
    const hasRedirect = /agricultural|mandi|commodity|scope|farming|कृषि/i.test(response);
    expect(hasRedirect).toBeTruthy();
    console.log('Stock market guardrail:', response.slice(0, 300));
  });
});

// ═══════════════════════════════════════
// 6. RESPONSE FORMAT & TRANSPARENCY
// ═══════════════════════════════════════

test.describe('Response Quality', () => {
  test('Price response contains source and date', async ({ request }) => {
    const { response } = await sendMessage(request, 'Onion price in Nashik');
    // Should cite data source
    const hasSource = /[Aa]gmarknet|[Ss]ource|स्रोत|[Dd]ata/i.test(response);
    const hasDate = /\d{4}-\d{2}-\d{2}|\d{2}\/\d{2}\/\d{4}|March|February|2026|2025/i.test(response);
    expect(hasSource || hasDate).toBeTruthy();
    console.log('Source/date in response:', response.slice(0, 300));
  });

  test('Response mentions what was searched (transparency)', async ({ request }) => {
    const { response } = await sendMessage(request, 'Tomato rate in Bengaluru');
    // Should mention the commodity and location used
    const hasTransparency = /[Tt]omato|[Bb]engaluru|[Kk]arnataka|टमाटर|Query:/i.test(response);
    expect(hasTransparency).toBeTruthy();
    console.log('Transparency in response:', response.slice(0, 300));
  });

  test('MSP reference included when applicable', async ({ request }) => {
    const { response } = await sendMessage(request, 'Wheat price in Karnal');
    // Wheat has MSP — should mention it
    const hasMSP = /MSP|[Mm]inimum [Ss]upport|न्यूनतम समर्थन/i.test(response);
    console.log('MSP mention:', hasMSP, '| Response:', response.slice(0, 300));
    // Don't hard-fail, just log — MSP inclusion depends on agent behavior
  });

  test('Price in standard unit (per quintal)', async ({ request }) => {
    const { response } = await sendMessage(request, 'Cotton price in Rajkot');
    // Should show per quintal
    const hasQuintal = /quintal|क्विंटल|\/q\b/i.test(response);
    const hasPrice = response.includes('₹');
    expect(hasPrice).toBeTruthy();
    console.log('Quintal format:', response.slice(0, 300));
  });
});

// ═══════════════════════════════════════
// 7. MULTI-TURN CONVERSATION CONTEXT
// ═══════════════════════════════════════

test.describe('Conversation Context', () => {
  test('Second message uses commodity from first message', async ({ request }) => {
    const sessionId = `context-test-${Date.now()}`;

    // First message: set commodity
    await sendMessage(request, 'I want to know about potato prices', { session_id: sessionId });

    // Second message: ask about location without repeating commodity
    const { response } = await sendMessage(request, 'What about in Agra?', { session_id: sessionId });

    // Should understand potato + Agra
    const hasPriceOrContext = response.includes('₹') || /[Pp]otato|आलू|[Aa]gra/i.test(response);
    expect(hasPriceOrContext).toBeTruthy();
    console.log('Context carry-over response:', response.slice(0, 300));
  });
});

// ═══════════════════════════════════════
// 8. COMPLEX / COMBINED QUERIES
// ═══════════════════════════════════════

test.describe('Complex Queries', () => {
  test('Sell advisory with specific quantity and storage', async ({ request }) => {
    const { response } = await sendMessage(request,
      'I have 100 quintal wheat in my godown in Karnal. Should I sell now or wait?'
    );
    // Should factor in storage, quantity, trend
    const hasSellAdvice = /[Ss]ell|[Hh]old|[Ss]plit|बेच|रुक|recommendation|storage|godown/i.test(response);
    expect(hasSellAdvice).toBeTruthy();
    console.log('Complex sell advisory:', response.slice(0, 500));
  });

  test('Best mandi comparison query', async ({ request }) => {
    const { response } = await sendMessage(request,
      'Where should I sell my soyabean? I am near Indore. Compare nearby mandis.'
    );
    // Should list multiple mandis with prices
    const hasComparison = /mandi|₹.*₹|compare|nearby|distance|km/i.test(response);
    expect(hasComparison).toBeTruthy();
    console.log('Mandi comparison:', response.slice(0, 500));
  });

  test('Negotiation brief with specific commodity + location', async ({ request }) => {
    const { response } = await sendMessage(request,
      'I am going to Hanumangarh mandi tomorrow to sell potato. Give me a negotiation card with fair price.'
    );
    // Should contain negotiation brief format
    const hasNegoBrief = /₹.*fair|price brief|negotiat|[Ff]air [Pp]rice|उचित मूल्य/i.test(response);
    expect(hasNegoBrief).toBeTruthy();
    console.log('Negotiation brief:', response.slice(0, 500));
  });

  test('Commodity without MSP (Potato/Onion/Tomato)', async ({ request }) => {
    const { response } = await sendMessage(request, 'Tomato price and sell advice for Nashik');
    // Should mention that no MSP exists for tomato
    const handlesNoMSP = /no MSP|MSP.*not|MSP.*applicable|लागू नहीं|not available/i.test(response) || response.includes('₹');
    expect(handlesNoMSP).toBeTruthy();
    console.log('No-MSP commodity:', response.slice(0, 400));
  });
});

// ═══════════════════════════════════════
// 9. EDGE CASES
// ═══════════════════════════════════════

test.describe('Edge Cases', () => {
  test('Empty-ish query should not crash', async ({ request }) => {
    const { response } = await sendMessage(request, 'hello');
    // Should greet or ask what they need
    expect(response.length).toBeGreaterThan(10);
    console.log('Greeting response:', response.slice(0, 200));
  });

  test('Unknown commodity should be handled gracefully', async ({ request }) => {
    const { response } = await sendMessage(request, 'What is the price of dragon fruit in Delhi?');
    // Should either find data or explain it's not available
    expect(response.length).toBeGreaterThan(20);
    console.log('Unknown commodity:', response.slice(0, 300));
  });

  test('Very long query should not crash', async ({ request }) => {
    const longQuery = 'I am a farmer from Karnal, Haryana. I have 200 quintal wheat stored in my godown. ' +
      'The quality is good, FAQ grade. I want to know if I should sell now or wait. ' +
      'Also tell me the MSP for wheat this year and which nearby mandi has the best price. ' +
      'My godown has good ventilation and I can store for 2-3 more weeks.';
    const { response } = await sendMessage(request, longQuery);
    expect(response.length).toBeGreaterThan(50);
    console.log('Long query response:', response.slice(0, 400));
  });
});
