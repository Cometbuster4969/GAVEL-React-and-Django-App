/**
 * Gavel E2E — Playwright-style browser test (also runnable via node with fetch).
 * Covers: login as each role → create → publish → start → ingest → process → review → adjudicate → complete → publish → audit
 * Requires: backend on 8000, frontend on 3000, Mongo (mongomock fallback works).
 * Run: npx playwright test e2e/gavel.spec.js  OR  node e2e/gavel.spec.js (API-only fallback)
 */

// Playwright test when available, otherwise API-only fallback
const isPlaywright = typeof test !== "undefined" && typeof expect !== "undefined";

async function apiLogin(email) {
    const r = await fetch("http://127.0.0.1:8000/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password: "gavel2026!" }),
    });
    if (!r.ok) throw new Error(`login ${email} failed ${r.status}`);
    const j = await r.json();
    return j.data.token;
}

async function runApiE2E() {
    const maya = await apiLogin("maya.chen@gavel.test");
    const jordan = await apiLogin("jordan.lee@gavel.test");
    const sam = await apiLogin("sam.rivera@gavel.test");
    const priya = await apiLogin("priya.shah@gavel.test");
    // Create
    const name = `E2E-${Date.now()}`;
    let r = await fetch("http://127.0.0.1:8000/api/v1/campaigns/create", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${maya}` },
        body: JSON.stringify({
            name,
            summary: "e2e",
            testCases: [{ id: "c1", title: "T", prompt: "Prompt" }],
            rubric: [
                { id: "r1", title: "R1", weight: 50, description: "" },
                { id: "r2", title: "R2", weight: 50, description: "" },
            ],
        }),
    });
    if (r.status !== 201) throw new Error(`create ${r.status} ${await r.text()}`);
    const campId = (await r.json()).data.id;
    // Publish + start
    for (const s of ["published", "running"]) {
        r = await fetch(`http://127.0.0.1:8000/api/v1/campaigns/${campId}/transition`, {
            method: "POST",
            headers: { "Content-Type": "application/json", Authorization: `Bearer ${maya}` },
            body: JSON.stringify({ status: s }),
        });
        if (!r.ok) throw new Error(`transition ${s} ${r.status} ${await r.text()}`);
    }
    // Ingest
    const items = [
        { caseId: "c1", modelName: "M1", output: "Out1", idempotencyKey: `k1-${Date.now()}` },
        { caseId: "c1", modelName: "M2", output: "Out2", idempotencyKey: `k2-${Date.now()}` },
    ];
    r = await fetch(`http://127.0.0.1:8000/api/v1/campaigns/${campId}/submissions`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${maya}` },
        body: JSON.stringify({ items }),
    });
    if (r.status !== 202) throw new Error(`ingest ${r.status}`);
    r = await fetch(`http://127.0.0.1:8000/api/v1/campaigns/${campId}/submissions/process`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${maya}` },
        body: JSON.stringify({ limit: 25 }),
    });
    if (!r.ok) throw new Error(`process ${r.status}`);
    // Reviews
    r = await fetch(`http://127.0.0.1:8000/api/v1/reviews?campaignId=${campId}`, {
        headers: { Authorization: `Bearer ${jordan}` },
    });
    let reviews = (await r.json()).data;
    if (reviews.items) reviews = reviews.items;
    const rid = reviews.find((x) => x.status === "available")?.id;
    if (!rid) throw new Error("no available review");
    r = await fetch(`http://127.0.0.1:8000/api/v1/reviews/${rid}/claim`, {
        method: "POST",
        headers: { Authorization: `Bearer ${jordan}` },
    });
    if (!r.ok) throw new Error(`claim ${r.status}`);
    r = await fetch(`http://127.0.0.1:8000/api/v1/reviews/${rid}/submit`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${jordan}` },
        body: JSON.stringify({ choice: "a", notes: "n", criterionScores: { r1: { a: 5, b: 3 }, r2: { a: 4, b: 4 } } }),
    });
    if (!r.ok) throw new Error(`submit j ${r.status} ${await r.text()}`);
    // Sam
    r = await fetch(`http://127.0.0.1:8000/api/v1/reviews?campaignId=${campId}`, {
        headers: { Authorization: `Bearer ${sam}` },
    });
    let revs = (await r.json()).data;
    if (revs.items) revs = revs.items;
    const avail = revs.find((x) => x.status === "available");
    if (avail) {
        let r2 = await fetch(`http://127.0.0.1:8000/api/v1/reviews/${avail.id}/claim`, {
            method: "POST",
            headers: { Authorization: `Bearer ${sam}` },
        });
        if (!r2.ok) throw new Error(`claim sam ${r2.status}`);
        r2 = await fetch(`http://127.0.0.1:8000/api/v1/reviews/${avail.id}/submit`, {
            method: "POST",
            headers: { "Content-Type": "application/json", Authorization: `Bearer ${sam}` },
            body: JSON.stringify({ choice: "b", notes: "n", criterionScores: { r1: { a: 2, b: 5 }, r2: { a: 3, b: 5 } } }),
        });
        if (!r2.ok) throw new Error(`submit sam ${r2.status}`);
        const dj = await r2.json();
        if (dj.data.disagreementDetected) {
            const adjs = await (await fetch(`http://127.0.0.1:8000/api/v1/adjudications?campaignId=${campId}`, { headers: { Authorization: `Bearer ${priya}` } })).json();
            let items = adjs.data.items || adjs.data;
            const open = items.find((x) => x.status === "open");
            if (open) {
                const rr = await fetch(`http://127.0.0.1:8000/api/v1/adjudications/${open.id}/resolve`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json", Authorization: `Bearer ${priya}` },
                    body: JSON.stringify({ choice: "a", rationale: "Rationale long enough for test." }),
                });
                if (!rr.ok) throw new Error(`resolve ${rr.status}`);
            }
        }
    }
    // Complete + publish
    r = await fetch(`http://127.0.0.1:8000/api/v1/campaigns/${campId}/transition`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${maya}` },
        body: JSON.stringify({ status: "completed" }),
    });
    if (!r.ok) throw new Error(`complete ${r.status} ${await r.text()}`);
    r = await fetch(`http://127.0.0.1:8000/api/v1/campaigns/${campId}/publish-results`, {
        method: "POST",
        headers: { Authorization: `Bearer ${maya}` },
    });
    if (r.status !== 201) throw new Error(`publish ${r.status}`);
    // Verify audit pagination
    const audit = await (await fetch("http://127.0.0.1:8000/api/v1/audit?limit=2", { headers: { Authorization: `Bearer ${maya}` } })).json();
    if (!audit.data.items || audit.data.items.length !== 2) throw new Error("audit pagination failed");
    console.log("API E2E passed for", campId);
    // Archive
    await fetch(`http://127.0.0.1:8000/api/v1/campaigns/${campId}/transition`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${maya}` },
        body: JSON.stringify({ status: "archived" }),
    });
}

if (isPlaywright) {
    // Browser E2E via Playwright
    const { test: pwTest, expect: pwExpect } = require("@playwright/test");
    pwTest("gavel full lifecycle", async ({ page }) => {
        // Login as Maya via UI
        await page.goto("http://127.0.0.1:3000/");
        await page.getByLabel("Work email").fill("maya.chen@gavel.test");
        await page.getByLabel("Password").fill("gavel2026!");
        await page.getByRole("button", { name: "Continue to workspace" }).click();
        await pwExpect(page.getByText("Campaigns")).toBeVisible({ timeout: 10000 });
        // API E2E also exercises backend, but UI check ensures frontend loads
        await runApiE2E();
        // Verify audit via UI
        await page.getByRole("button", { name: "Audit history" }).click();
        await pwExpect(page.getByText("Audit history")).toBeVisible();
    });
} else if (require.main === module) {
    // Node direct run
    runApiE2E()
        .then(() => console.log("E2E success"))
        .catch((e) => {
            console.error("E2E failed", e);
            process.exit(1);
        });
}

module.exports = { runApiE2E };
