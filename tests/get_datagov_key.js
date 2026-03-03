/**
 * MandiMitra — Get data.gov.in API Key
 * Uses Playwright to register at data.gov.in and obtain an API key.
 *
 * Usage:
 *   node tests/get_datagov_key.js
 */
const { chromium } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

const SCREENSHOT_DIR = 'tests/screenshots/datagov';

async function getApiKey() {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });

  const browser = await chromium.launch({ headless: false, slowMo: 300 });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 }
  });
  const page = await context.newPage();

  const screenshot = async (name) => {
    const p = path.join(SCREENSHOT_DIR, `${name}.png`);
    await page.screenshot({ path: p, fullPage: true });
    console.log(`Screenshot: ${p}`);
  };

  try {
    // Step 1: Check the current API key usage
    console.log('\n=== Step 1: Check current API key ===');
    await page.goto('https://data.gov.in/user/me/api-key', { waitUntil: 'domcontentloaded', timeout: 30000 });
    await screenshot('01_check_existing');
    const currentText = await page.evaluate(() => document.body.innerText);
    console.log('Page content:', currentText.substring(0, 300));

    // Step 2: Try the registration page
    console.log('\n=== Step 2: Registration page ===');
    await page.goto('https://data.gov.in/user/register', { waitUntil: 'domcontentloaded', timeout: 30000 });
    await screenshot('02_register_page');

    const regText = await page.evaluate(() => document.body.innerText);
    console.log('Registration page:', regText.substring(0, 400));

    // Find form fields
    const inputs = await page.$$eval('input:not([type="hidden"])', els =>
      els.map(e => ({ id: e.id, name: e.name, type: e.type, placeholder: e.placeholder, label: e.getAttribute('aria-label') }))
    );
    console.log('Form fields:', JSON.stringify(inputs.filter(i => i.name || i.id), null, 2));

    // Step 3: Try to fill registration form
    const emailInput = page.locator('input[name="mail"], input[type="email"], input[id="edit-mail"]').first();
    const nameInput = page.locator('input[name="name"], input[id="edit-name"]').first();
    const passInput = page.locator('input[name="pass"], input[type="password"]').first();

    const email = `mandimitra.hackathon.${Date.now()}@protonmail.com`;
    const username = `mandimitra${Date.now()}`;
    const password = `MandiMitra2026!`;

    if (await emailInput.isVisible({ timeout: 3000 }).catch(() => false)) {
      await emailInput.fill(email);
      console.log(`Filled email: ${email}`);
    }

    if (await nameInput.isVisible({ timeout: 3000 }).catch(() => false)) {
      await nameInput.fill(username);
      console.log(`Filled username: ${username}`);
    }

    if (await passInput.isVisible({ timeout: 3000 }).catch(() => false)) {
      await passInput.fill(password);
      console.log('Filled password');
    }

    await screenshot('03_filled_form');

    // Step 4: Look for alternative - direct API key lookup
    console.log('\n=== Step 4: Try direct API resource access ===');
    const testUrl = 'https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070?api-key=579b464db66ec23bdd000001cdd3946e44ce4aad7209ff7b23ac571b&format=json&limit=2&filters[commodity]=Wheat&filters[state.keyword]=Madhya Pradesh&filters[arrival_date]=01/03/2026';

    await page.goto(testUrl, { waitUntil: 'domcontentloaded', timeout: 15000 });
    await screenshot('04_api_test');

    const apiResponse = await page.evaluate(() => document.body.innerText);
    console.log('\nAPI test response:', apiResponse.substring(0, 500));

    // Check rate limit or success
    if (apiResponse.includes('"total"')) {
      const data = JSON.parse(apiResponse);
      console.log(`\nAPI working! Total records: ${data.total}, Got: ${data.count}`);
      console.log('Records:', JSON.stringify(data.records?.slice(0, 2), null, 2));
    } else if (apiResponse.includes('429') || apiResponse.includes('rate')) {
      console.log('\nRate limited with current key. Need new API key.');
    }

    // Step 5: Try the API key registration via data.gov.in web interface
    console.log('\n=== Step 5: Check data.gov.in main page ===');
    await page.goto('https://data.gov.in', { waitUntil: 'domcontentloaded', timeout: 30000 });
    await screenshot('05_main_page');

    // Look for API section
    const apiLinks = await page.$$eval('a', links =>
      links.map(l => ({ text: l.textContent.trim(), href: l.href }))
           .filter(l => l.text.toLowerCase().includes('api') || l.href.includes('api'))
           .slice(0, 10)
    );
    console.log('API-related links:', JSON.stringify(apiLinks, null, 2));

    // Step 6: Try API key from GET request
    console.log('\n=== Step 6: Try fetching with slower rate ===');
    const testUrl2 = 'https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070?api-key=579b464db66ec23bdd000001cdd3946e44ce4aad7209ff7b23ac571b&format=json&limit=5&filters[arrival_date]=28/02/2026';

    await page.goto(testUrl2, { waitUntil: 'domcontentloaded', timeout: 15000 });
    await screenshot('06_broad_fetch_test');

    const broadResponse = await page.evaluate(() => document.body.innerText);
    console.log('\nBroad fetch response:', broadResponse.substring(0, 600));

    // Save findings to file
    const findings = {
      timestamp: new Date().toISOString(),
      currentApiKey: '579b464db66ec23bdd000001cdd3946e44ce4aad7209ff7b23ac571b',
      registrationEmail: email,
      registrationUsername: username,
      apiTestResult: apiResponse.substring(0, 200),
      broadFetchResult: broadResponse.substring(0, 200),
    };

    fs.writeFileSync('tests/datagov_findings.json', JSON.stringify(findings, null, 2));
    console.log('\nFindings saved to tests/datagov_findings.json');

  } catch (e) {
    console.error('\nError:', e.message);
    await screenshot('error');
  } finally {
    await browser.close();
  }
}

getApiKey().catch(e => {
  console.error('Fatal error:', e);
  process.exit(1);
});
