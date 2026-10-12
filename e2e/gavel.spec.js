/**
 * Gavel E2E — Lifecycle test (runnable via node with built-in fetch or as a Playwright spec).
 * Covers: login as each role → create → publish → start → ingest → process →
 *         review (Jordan) → opposite review (Sam) → disagreement detected →
 *         adjudicate (Priya) → complete → publish results → audit cursor pagination → archive.
 *
 * Optional live check against a running app. Prefer `bun test` for the isolated
 * suite. This walkthrough uses demo accounts and will leave campaigns behind
 * unless you reseed (`bun run seed`).
 *
 * Run: bun run test:e2e
 */

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

    // 1. Create campaign
    const name = `E2E-${Date.now()}`;
    let r = await fetch("http://127.0.0.1:8000/api/v1/campaigns/create", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${maya}` },
        body: JSON.stringify({
            name,
            summary: "End-to-end evaluation lifecycle verification",
            testCases: [{ id: "c1", title: "Test Case 1", prompt: "Explain quantum computing briefly." }],
            rubric: [
                { id: "r1", title: "Accuracy", weight: 50, description: "Factual correctness" },
                { id: "r2", title: "Clarity", weight: 50, description: "Readability and tone" },
            ],
        }),
    });
    if (r.status !== 201) throw new Error(`create failed ${r.status} ${await r.text()}`);
    const campId = (await r.json()).data.id;

    // 2. Publish and start
    for (const s of ["published", "running"]) {
        r = await fetch(`http://127.0.0.1:8000/api/v1/campaigns/${campId}/transition`, {
            method: "POST",
            headers: { "Content-Type": "application/json", Authorization: `Bearer ${maya}` },
            body: JSON.stringify({ status: s }),
        });
        if (!r.ok) throw new Error(`transition to ${s} failed: ${r.status} ${await r.text()}`);
    }

    // 3. Ingest submissions
    const items = [
        { caseId: "c1", modelName: "Model-A", output: "Quantum computers use qubits to compute in parallel.", idempotencyKey: `k1-${Date.now()}` },
        { caseId: "c1", modelName: "Model-B", output: "Quantum computers exploit superposition and entanglement.", idempotencyKey: `k2-${Date.now()}` },
    ];
    r = await fetch(`http://127.0.0.1:8000/api/v1/campaigns/${campId}/submissions`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${maya}` },
        body: JSON.stringify({ items }),
    });
    if (r.status !== 202) throw new Error(`ingest failed ${r.status}`);

    // 4. Process queue to generate review pairs
    r = await fetch(`http://127.0.0.1:8000/api/v1/campaigns/${campId}/submissions/process`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${maya}` },
        body: JSON.stringify({ limit: 25 }),
    });
    if (!r.ok) throw new Error(`process failed ${r.status}`);

    // 5. Jordan (Reviewer 1) claims and submits review
    r = await fetch(`http://127.0.0.1:8000/api/v1/reviews?campaignId=${campId}`, {
        headers: { Authorization: `Bearer ${jordan}` },
    });
    let reviews = (await r.json()).data;
    if (reviews.items) reviews = reviews.items;
    const rid = reviews.find((x) => x.status === "available")?.id;
    if (!rid) throw new Error("no available review assignment for Jordan");

    r = await fetch(`http://127.0.0.1:8000/api/v1/reviews/${rid}/claim`, {
        method: "POST",
        headers: { Authorization: `Bearer ${jordan}` },
    });
    if (!r.ok) throw new Error(`Jordan claim failed ${r.status}`);

    r = await fetch(`http://127.0.0.1:8000/api/v1/reviews/${rid}/submit`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${jordan}` },
        body: JSON.stringify({
            choice: "a",
            notes: "Jordan preference notes",
            criterionScores: { r1: { a: 5, b: 3 }, r2: { a: 4, b: 4 } },
        }),
    });
    if (!r.ok) throw new Error(`Jordan submit failed ${r.status} ${await r.text()}`);
    const jordanResult = (await r.json()).data;
    const preferredOutput = jordanResult.review.left.output;

    // 6. Sam (Reviewer 2) claims opposite side to trigger disagreement
    r = await fetch(`http://127.0.0.1:8000/api/v1/reviews?campaignId=${campId}`, {
        headers: { Authorization: `Bearer ${sam}` },
    });
    let revs = (await r.json()).data;
    if (revs.items) revs = revs.items;
    const avail = revs.find((x) => x.status === "available");
    if (!avail) throw new Error("second reviewer assignment missing for Sam");

    r = await fetch(`http://127.0.0.1:8000/api/v1/reviews/${avail.id}/claim`, {
        method: "POST",
        headers: { Authorization: `Bearer ${sam}` },
    });
    if (!r.ok) throw new Error(`Sam claim failed ${r.status}`);
    const samClaim = (await r.json()).data;
    const samChoice = samClaim.left.output === preferredOutput ? "b" : "a";

    r = await fetch(`http://127.0.0.1:8000/api/v1/reviews/${avail.id}/submit`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${sam}` },
        body: JSON.stringify({
            choice: samChoice,
            notes: "Sam opposite preference notes",
            criterionScores: { r1: { a: 2, b: 5 }, r2: { a: 3, b: 5 } },
        }),
    });
    if (!r.ok) throw new Error(`Sam submit failed ${r.status}`);
    const dj = await r.json();
    if (!dj.data.disagreementDetected) throw new Error("expected disagreement was not detected");

    // 7. Priya (Adjudicator) resolves disagreement
    const adjs = await (await fetch(`http://127.0.0.1:8000/api/v1/adjudications?campaignId=${campId}`, {
        headers: { Authorization: `Bearer ${priya}` },
    })).json();
    let adjItems = adjs.data.items || adjs.data;
    const open = adjItems.find((x) => x.status === "open");
    if (!open) throw new Error("expected open adjudication missing");

    r = await fetch(`http://127.0.0.1:8000/api/v1/adjudications/${open.id}/resolve`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${priya}` },
        body: JSON.stringify({ choice: "a", rationale: "Adjudication decision based on accuracy rubric." }),
    });
    if (!r.ok) throw new Error(`adjudication resolve failed ${r.status}`);

    // 8. Complete and publish results
    r = await fetch(`http://127.0.0.1:8000/api/v1/campaigns/${campId}/transition`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${maya}` },
        body: JSON.stringify({ status: "completed" }),
    });
    if (!r.ok) throw new Error(`complete failed ${r.status} ${await r.text()}`);

    r = await fetch(`http://127.0.0.1:8000/api/v1/campaigns/${campId}/publish-results`, {
        method: "POST",
        headers: { Authorization: `Bearer ${maya}` },
    });
    if (r.status !== 201) throw new Error(`publish results failed ${r.status}`);

    // 9. Verify audit pagination and cursor
    const audit = await (await fetch("http://127.0.0.1:8000/api/v1/audit?limit=2", {
        headers: { Authorization: `Bearer ${maya}` },
    })).json();
    if (!audit.data.items || audit.data.items.length !== 2) throw new Error("audit pagination limit failed");
    if (audit.data.nextCursor) {
        const next = await (await fetch(`http://127.0.0.1:8000/api/v1/audit?limit=2&cursor=${audit.data.nextCursor}`, {
            headers: { Authorization: `Bearer ${maya}` },
        })).json();
        if (!next.data.items.length || next.data.items.some((item) => audit.data.items.some((first) => first.id === item.id))) {
            throw new Error("audit cursor repeated rows or skipped page");
        }
    }

    // 10. Archive campaign
    const archived = await fetch(`http://127.0.0.1:8000/api/v1/campaigns/${campId}/transition`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${maya}` },
        body: JSON.stringify({ status: "archived" }),
    });
    if (!archived.ok) throw new Error(`archive failed ${archived.status}`);

    console.log("Full E2E lifecycle completed successfully for campaign", campId);
}

if (isPlaywright) {
    test("gavel full lifecycle", async ({ page }) => {
        const errors = [];
        page.on("pageerror", (error) => errors.push(error.message));
        await page.goto("http://127.0.0.1:3000/");
        await page.getByLabel("Work email").fill("maya.chen@gavel.test");
        await page.getByLabel("Password", { exact: true }).fill("gavel2026!");
        await page.getByRole("button", { name: "Continue to workspace" }).click();
        await expect(page.getByRole("button", { name: "Campaigns", exact: true })).toBeVisible();
        await runApiE2E();
        for (const name of ["Campaigns", "Adjudication", "Results", "Audit history", "Overview"]) {
            await page.getByRole("button", { name, exact: true }).click();
            await expect(page.locator("h1")).toBeVisible();
        }
        expect(errors).toEqual([]);
    });
} else if (require.main === module) {
    runApiE2E()
        .then(() => console.log("E2E success"))
        .catch((e) => {
            console.error("E2E failed:", e);
            process.exit(1);
        });
}

module.exports = { runApiE2E };
