import { useState, useEffect } from "react";
import { Icon, StatusPill, PageHeading } from "../components/ui.jsx";

export function AdjudicationPage({ items, loading, onResolve, busy, canResolve }) {
	const [activeId, setActiveId] = useState("");
	const [choice, setChoice] = useState("");
	const [rationale, setRationale] = useState("");
	const open = items.filter((item) => item.status === "open");
	const active = open.find((item) => item.id === activeId) || open[0];
	useEffect(() => {
		setChoice("");
		setRationale("");
	}, [active?.id]);
	return (
		<div className="page-content">
			<PageHeading
				eyebrow="QUALITY CONTROL"
				title="Adjudication"
				description="Resolve reviewer disagreements with a recorded final decision and rationale."
				action={
					<span className="adjudication-open-count">
						<i />
						{open.length} open case{open.length === 1 ? "" : "s"}
					</span>
				}
			/>
			{loading ? (
				<div className="panel empty-state">
					<span className="spinner" />
					Loading disagreements…
				</div>
			) : !active ? (
				<div className="panel adjudication-empty">
					<span className="review-empty-icon">
						<Icon name="scale" size={24} />
					</span>
					<h2>All aligned</h2>
					<p>No open reviewer disagreements. New cases are created automatically when pairwise votes conflict.</p>
				</div>
			) : (
				<div className="adjudication-layout">
					<aside className="panel adjudication-list" aria-label="Adjudication queue">
						<div className="panel-heading">
							<div>
								<span className="eyebrow">REQUIRES DECISION</span>
								<h2>Open cases</h2>
							</div>
							<span className="small-count">{open.length}</span>
						</div>
						{open.map((item) => (
							<button
								className={`adjudication-list-item ${active.id === item.id ? "active" : ""}`}
								key={item.id}
								type="button"
								onClick={() => setActiveId(item.id)}
							>
								<span className="adjudication-case-mark">
									<Icon name="scale" size={17} />
								</span>
								<span>
									<strong>{item.campaignName}</strong>
									<small>{item.caseId} · Disagreement detected</small>
								</span>
								<Icon name="chevron" size={15} />
							</button>
						))}
					</aside>
					<section className="panel adjudication-workspace">
						<div className="adjudication-case-head">
							<div>
								<span className="eyebrow">
									{active.campaignName} · {active.caseId}
								</span>
								<h2>Make the final call</h2>
							</div>
							<StatusPill status="open" />
						</div>
						<div className="review-prompt adjudication-prompt">
							<span className="prompt-label">ORIGINAL TEST CASE</span>
							<p>{active.prompt}</p>
						</div>
						<p className="adjudication-helper">
							Two reviewers preferred different responses.{" "}
							{canResolve
								? "Choose the stronger response using the campaign’s scoring rubric."
								: "This is read-only for campaign owners; an adjudicator must record the final decision."}
						</p>
						<div className="response-grid adjudication-responses">
							{[
								["a", active.left],
								["b", active.right],
							].map(([side, response]) => (
								<button
									className={`response-card adjudication-response ${choice === side ? "response-selected" : ""}`}
									type="button"
									key={side}
									disabled={!canResolve}
									onClick={() => setChoice(side)}
								>
									<span className="response-card-head">
										<span className="response-label">
											<i>{side.toUpperCase()}</i>
											{response.label}
										</span>
										<span className={`radio-dot ${choice === side ? "checked" : ""}`}>{choice === side && <i />}</span>
									</span>
									<span className="response-copy">{response.output}</span>
								</button>
							))}
						</div>
						<label className="rationale-label" htmlFor="adjudication-rationale">
							Decision rationale <span>Required · added to the permanent audit history</span>
						</label>
						<textarea
							className="rationale-field"
							id="adjudication-rationale"
							rows={3}
							maxLength={1200}
							placeholder="Explain how the selected response better meets the evaluation rubric…"
							value={rationale}
							disabled={!canResolve}
							onChange={(event) => setRationale(event.target.value)}
						/>
						<div className="adjudication-footer">
							<span>
								<Icon name="shield" size={15} />
								This decision is immutable once recorded
							</span>
							<button
								className="button button-primary"
								type="button"
								disabled={!canResolve || !choice || rationale.trim().length < 8 || busy}
								onClick={() => onResolve(active, choice, rationale)}
							>
								{busy ? "Recording decision…" : canResolve ? "Record final decision" : "Adjudicator decision required"}
								<Icon name="arrow" size={16} />
							</button>
						</div>
					</section>
				</div>
			)}
			{items.some((item) => item.status === "resolved") && (
				<section className="panel resolved-panel">
					<div className="panel-heading">
						<div>
							<span className="eyebrow">DECISION HISTORY</span>
							<h2>Recently resolved</h2>
						</div>
						<span className="small-count">{items.filter((item) => item.status === "resolved").length}</span>
					</div>
					{items
						.filter((item) => item.status === "resolved")
						.slice(0, 4)
						.map((item) => (
							<div className="resolved-row" key={item.id}>
								<span className="resolved-icon">
									<Icon name="check" size={16} />
								</span>
								<span>
									<strong>{item.campaignName}</strong>
									<small>{item.caseId} · Final decision recorded</small>
								</span>
								<StatusPill status="resolved" />
							</div>
						))}
				</section>
			)}
		</div>
	);
}
