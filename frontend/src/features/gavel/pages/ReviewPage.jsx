import { useState, useEffect } from "react";
import { Icon, StatusPill, PageHeading } from "../components/ui.jsx";

export function ReviewPage({ reviews, loading, activeReviewId, onSelect, onClaim, onRelease, onSubmit, busy }) {
	const [choice, setChoice] = useState("");
	const [notes, setNotes] = useState("");
	const [criterionScores, setCriterionScores] = useState({});
	const active = reviews.find((item) => item.id === activeReviewId);
	useEffect(() => {
		setChoice("");
		setNotes("");
		setCriterionScores(Object.fromEntries((active?.rubric || []).map((criterion) => [criterion.id, { a: "", b: "" }])));
	}, [activeReviewId, active?.rubric]);
	const available = reviews.filter((item) => item.status === "available");
	const mine = reviews.filter((item) => item.status === "claimed" && item.claimedByMe);
	const complete = reviews.filter((item) => item.status === "completed");
	return (
		<div className="page-content review-page">
			<PageHeading
				eyebrow="HUMAN EVALUATION"
				title="Blind review"
				description="Compare model responses without seeing which system produced them."
			/>
			<div className="review-layout">
				<aside className="review-queue panel" aria-label="Blind review queue">
					<div className="review-queue-head">
						<div>
							<span className="eyebrow">YOUR QUEUE</span>
							<h2>Comparisons</h2>
						</div>
						<span className="small-count">{available.length + mine.length} open</span>
					</div>
					{loading ? (
						<div className="empty-state">
							<span className="spinner" />
							Loading queue…
						</div>
					) : (
						<>
							<QueueSection title="In progress" items={mine} activeId={activeReviewId} onSelect={onSelect} />
							<QueueSection title="Ready to claim" items={available} activeId={activeReviewId} onSelect={onSelect} />
							<QueueSection
								title="Recently reviewed"
								items={complete.slice(0, 4)}
								activeId={activeReviewId}
								onSelect={onSelect}
							/>
							{!reviews.length && (
								<div className="empty-inline">
									<strong>No comparisons yet</strong>
									<span>New assignments appear here when response processing is complete.</span>
								</div>
							)}
						</>
					)}
				</aside>
				<section className="review-workspace">
					{!active ? (
						<div className="panel review-empty">
							<span className="review-empty-icon">
								<Icon name="compare" size={25} />
							</span>
							<h2>Select a comparison</h2>
							<p>
								Claim a ready assignment to begin a blind review. Model identities stay hidden until results are published.
							</p>
						</div>
					) : (
						<>
							<div className="review-context">
								<div>
									<span className="eyebrow">{active.campaignName}</span>
									<h2>{active.status === "completed" ? "Your completed review" : "Which response is stronger?"}</h2>
								</div>
								<StatusPill status={active.status} />
							</div>
							<div className="blind-callout">
								<Icon name="shield" size={17} />
								<span>
									<strong>Blind review enabled</strong> — model names and response order are independently randomized for
									each reviewer.
								</span>
							</div>
							<div className="review-prompt">
								<span className="prompt-label">TEST CASE · {active.caseId}</span>
								<p>{active.prompt}</p>
							</div>
							<div className="response-grid">
								{[
									["a", active.left],
									["b", active.right],
								].map(([side, response]) => (
									<article className={`response-card ${choice === side ? "response-selected" : ""}`} key={side}>
										<div className="response-card-head">
											<span className="response-label">
												<i>{side.toUpperCase()}</i>
												{response.label}
											</span>
											{active.status !== "completed" && (
												<button
													type="button"
													className={`select-response ${choice === side ? "chosen" : ""}`}
													onClick={() => active.status === "claimed" && setChoice(side)}
													disabled={active.status !== "claimed"}
													aria-pressed={choice === side}
												>
													{choice === side ? <Icon name="check" size={15} /> : "Choose"}
												</button>
											)}
										</div>
										<p>{response.output}</p>
									</article>
								))}
							</div>
							<div className="rubric-review">
								<div className="rubric-review-head">
									<div>
										<span className="eyebrow">EVALUATION RUBRIC</span>
										<strong>Consider each dimension</strong>
									</div>
									<span>v{active.rubricVersion}</span>
								</div>
								<div className="rubric-chip-list">
									{active.rubric.map((criterion) => (
										<span className="rubric-chip" key={criterion.id}>
											<b>{criterion.weight}%</b>
											{criterion.title}
										</span>
									))}
								</div>
								{active.status === "claimed" && (
									<div className="criterion-score-list">
										{active.rubric.map((criterion) => (
											<div className="criterion-score-row" key={criterion.id}>
												<strong>{criterion.title}</strong>
												<label>
													Response A
													<input
														type="number"
														min="1"
														max="5"
														value={criterionScores[criterion.id]?.a || ""}
														onChange={(event) =>
															setCriterionScores((current) => ({
																...current,
																[criterion.id]: { ...current[criterion.id], a: event.target.value },
															}))
														}
													/>
												</label>
												<label>
													Response B
													<input
														type="number"
														min="1"
														max="5"
														value={criterionScores[criterion.id]?.b || ""}
														onChange={(event) =>
															setCriterionScores((current) => ({
																...current,
																[criterion.id]: { ...current[criterion.id], b: event.target.value },
															}))
														}
													/>
												</label>
											</div>
										))}
									</div>
								)}
							</div>
							{active.status === "available" && (
								<button
									type="button"
									className="button button-primary claim-button"
									disabled={busy}
									onClick={() => onClaim(active)}
								>
									{busy ? "Claiming assignment…" : "Claim this review"}
									<Icon name="arrow" size={16} />
								</button>
							)}
							{active.status === "claimed" && (
								<div className="review-submit">
									<label htmlFor="review-notes">
										Decision notes <span>Optional · visible to adjudicators if there is disagreement</span>
									</label>
									<textarea
										id="review-notes"
										maxLength={1200}
										rows={3}
										placeholder="What made this response stronger?"
										value={notes}
										onChange={(event) => setNotes(event.target.value)}
									/>
									<div className="review-submit-foot">
										<span>{choice ? `Response ${choice.toUpperCase()} selected` : "Select a response to submit"}</span>
										<div className="review-submit-actions">
											<button
												type="button"
												className="button button-outline"
												disabled={busy}
												onClick={() => onRelease(active)}
											>
												Release
											</button>
											<button
												type="button"
												className="button button-primary"
												disabled={!choice || busy}
												onClick={() => onSubmit(active, choice, notes, criterionScores)}
											>
												{busy ? "Submitting…" : "Submit evaluation"}
												<Icon name="arrow" size={16} />
											</button>
										</div>
									</div>
								</div>
							)}
							{active.status === "completed" && (
								<div className="completed-review-note">
									<Icon name="check" size={16} />
									You submitted this review. Thank you for helping improve evaluation confidence.
								</div>
							)}
						</>
					)}
				</section>
			</div>
		</div>
	);
}

export function QueueSection({ title, items, activeId, onSelect }) {
	if (!items.length) return null;
	return (
		<div className="queue-section">
			<h3>
				{title}
				<span>{items.length}</span>
			</h3>
			{items.map((item) => (
				<button
					type="button"
					key={item.id}
					className={`queue-item ${activeId === item.id ? "active" : ""}`}
					onClick={() => onSelect(item)}
				>
					<span className="queue-item-mark">
						<Icon name="compare" size={16} />
					</span>
					<span>
						<strong>{item.campaignName}</strong>
						<small>
							{item.caseId} ·{" "}
							{item.status === "completed"
								? "Submitted"
								: item.status === "claimed"
									? "Claimed by you"
									: "Pairwise preference"}
						</small>
					</span>
					<Icon name="chevron" size={15} />
				</button>
			))}
		</div>
	);
}
