import { useState } from "react";
import { Icon } from "../components/ui.jsx";

export function CampaignModal({ onClose, onCreate, busy }) {
	const [name, setName] = useState("");
	const [summary, setSummary] = useState("");
	const [prompt, setPrompt] = useState("");
	const [error, setError] = useState("");
	const submit = async (event) => {
		event.preventDefault();
		try {
			await onCreate({
				name,
				summary,
				testCases: [{ id: "case-1", title: "Core scenario", prompt }],
				rubric: [
					{ id: "helpfulness", title: "Helpfulness", weight: 40, description: "Moves the user toward a useful resolution." },
					{ id: "accuracy", title: "Accuracy", weight: 35, description: "Stays grounded in the available information." },
					{ id: "clarity", title: "Clarity", weight: 25, description: "Communicates in a concise, actionable way." },
				],
			});
		} catch (failure) {
			setError(failure.message);
		}
	};
	return (
		<div className="modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
			<section className="modal-card" role="dialog" aria-modal="true" aria-labelledby="new-campaign-title">
				<div className="modal-head">
					<span className="modal-mark">
						<Icon name="layers" size={19} />
					</span>
					<button className="icon-quiet" type="button" onClick={onClose} aria-label="Close dialog">
						<Icon name="close" size={19} />
					</button>
				</div>
				<span className="eyebrow">NEW EVALUATION</span>
				<h2 id="new-campaign-title">Start with a clear question.</h2>
				<p className="modal-copy">Create a draft campaign. Add a weighted rubric and at least one test case before publishing.</p>
				<form className="modal-form" onSubmit={submit}>
					<label htmlFor="campaign-name">Campaign name</label>
					<input
						id="campaign-name"
						autoFocus
						maxLength={120}
						required
						minLength={3}
						placeholder="e.g. Support response quality"
						value={name}
						onChange={(event) => setName(event.target.value)}
					/>
					<label htmlFor="campaign-summary">What are you evaluating?</label>
					<input
						id="campaign-summary"
						maxLength={500}
						placeholder="A short description for your team"
						value={summary}
						onChange={(event) => setSummary(event.target.value)}
					/>
					<label htmlFor="campaign-prompt">
						First test case <span>Prompt or user scenario</span>
					</label>
					<textarea
						id="campaign-prompt"
						rows={4}
						required
						minLength={3}
						placeholder="Describe the user scenario or task to evaluate…"
						value={prompt}
						onChange={(event) => setPrompt(event.target.value)}
					/>
					{error && (
						<p className="form-error" role="alert">
							{error}
						</p>
					)}
					<div className="modal-actions">
						<button className="button button-outline" type="button" onClick={onClose}>
							Cancel
						</button>
						<button className="button button-primary" type="submit" disabled={busy}>
							{busy ? "Creating…" : "Create draft"}
							<Icon name="arrow" size={16} />
						</button>
					</div>
				</form>
			</section>
		</div>
	);
}
