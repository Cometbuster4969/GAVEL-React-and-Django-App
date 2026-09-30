import { useState } from "react";
import { Icon } from "../components/ui.jsx";

export function CampaignEditorModal({ campaign, onClose, onSave, busy }) {
	const [name, setName] = useState(campaign.name);
	const [summary, setSummary] = useState(campaign.summary);
	const [cases, setCases] = useState(campaign.testCases.map((item) => ({ ...item })));
	const [rubric, setRubric] = useState(campaign.rubric.map((item) => ({ ...item })));
	const [error, setError] = useState("");
	const total = rubric.reduce((sum, item) => sum + (Number(item.weight) || 0), 0);
	const updateCase = (index, key, value) =>
		setCases((items) => items.map((item, itemIndex) => (itemIndex === index ? { ...item, [key]: value } : item)));
	const updateCriterion = (index, key, value) =>
		setRubric((items) =>
			items.map((item, itemIndex) => (itemIndex === index ? { ...item, [key]: key === "weight" ? Number(value) : value } : item)),
		);
	const addCase = () =>
		setCases((items) => [...items, { id: `case-${crypto.randomUUID().slice(0, 8)}`, title: "New test case", prompt: "" }]);
	const addCriterion = () =>
		setRubric((items) => [
			...items,
			{ id: `criterion-${crypto.randomUUID().slice(0, 8)}`, title: "New criterion", weight: 1, description: "" },
		]);
	const save = async (event) => {
		event.preventDefault();
		setError("");
		try {
			await onSave({ name, summary, testCases: cases, rubric });
		} catch (failure) {
			setError(failure.message);
		}
	};
	return (
		<div className="modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
			<section
				className="modal-card modal-wide definition-modal"
				role="dialog"
				aria-modal="true"
				aria-labelledby="edit-campaign-title"
			>
				<div className="modal-head">
					<span className="modal-mark">
						<Icon name="layers" size={19} />
					</span>
					<button className="icon-quiet" type="button" onClick={onClose} aria-label="Close dialog">
						<Icon name="close" size={19} />
					</button>
				</div>
				<span className="eyebrow">DRAFT DEFINITION · V{campaign.version}</span>
				<h2 id="edit-campaign-title">Shape the evaluation.</h2>
				<p className="modal-copy">
					Suite and rubric versions increment when saved. Definitions lock when the campaign is published.
				</p>
				<form className="modal-form" onSubmit={save}>
					<label htmlFor="edit-campaign-name">Campaign name</label>
					<input
						id="edit-campaign-name"
						required
						minLength={3}
						maxLength={120}
						value={name}
						onChange={(event) => setName(event.target.value)}
					/>
					<label htmlFor="edit-campaign-summary">Description</label>
					<input
						id="edit-campaign-summary"
						maxLength={500}
						value={summary}
						onChange={(event) => setSummary(event.target.value)}
					/>
					<div className="editor-section-head">
						<div>
							<span className="eyebrow">VERSIONED TEST SUITE</span>
							<span className="editor-section-title">Test cases</span>
						</div>
						<button className="text-button" type="button" onClick={addCase}>
							<Icon name="plus" size={14} />
							Add case
						</button>
					</div>
					<div className="editor-items">
						{cases.map((item, index) => (
							<div className="editor-case" key={item.id}>
								<div className="editor-case-top">
									<span className="case-index">{String(index + 1).padStart(2, "0")}</span>
									<input
										aria-label={`Test case ${index + 1} title`}
										maxLength={120}
										value={item.title}
										onChange={(event) => updateCase(index, "title", event.target.value)}
									/>
									{cases.length > 1 && (
										<button
											className="icon-quiet editor-remove"
											type="button"
											aria-label={`Remove test case ${index + 1}`}
											onClick={() => setCases((items) => items.filter((_, itemIndex) => itemIndex !== index))}
										>
											<Icon name="close" size={15} />
										</button>
									)}
								</div>
								<textarea
									aria-label={`Test case ${index + 1} prompt`}
									rows={2}
									value={item.prompt}
									onChange={(event) => updateCase(index, "prompt", event.target.value)}
									placeholder="Describe the scenario or evaluation prompt…"
								/>
							</div>
						))}
					</div>
					<div className="editor-section-head rubric-editor-head">
						<div>
							<span className="eyebrow">WEIGHTED SCORING</span>
							<span className="editor-section-title">Rubric criteria</span>
						</div>
						<div className={`weight-total ${total === 100 ? "balanced" : ""}`}>
							{total}% / 100%{" "}
							<button className="text-button" type="button" onClick={addCriterion}>
								<Icon name="plus" size={14} />
								Add
							</button>
						</div>
					</div>
					<div className="editor-items">
						{rubric.map((item, index) => (
							<div className="editor-criterion" key={item.id}>
								<div>
									<input
										aria-label={`Criterion ${index + 1} name`}
										maxLength={80}
										value={item.title}
										onChange={(event) => updateCriterion(index, "title", event.target.value)}
									/>
									<input
										aria-label={`Criterion ${index + 1} weight`}
										type="number"
										min="1"
										max="100"
										value={item.weight}
										onChange={(event) => updateCriterion(index, "weight", event.target.value)}
									/>
									<span>%</span>
									{rubric.length > 1 && (
										<button
											className="icon-quiet editor-remove"
											type="button"
											aria-label={`Remove criterion ${index + 1}`}
											onClick={() => setRubric((items) => items.filter((_, itemIndex) => itemIndex !== index))}
										>
											<Icon name="close" size={15} />
										</button>
									)}
								</div>
								<input
									className="criterion-description"
									aria-label={`Criterion ${index + 1} guidance`}
									maxLength={240}
									value={item.description}
									onChange={(event) => updateCriterion(index, "description", event.target.value)}
									placeholder="Guidance for reviewers"
								/>
							</div>
						))}
					</div>
					{total > 100 && <p className="form-error">Rubric weights exceed 100%. Reduce a criterion weight before saving.</p>}
					{error && (
						<p className="form-error" role="alert">
							{error}
						</p>
					)}
					<div className="modal-actions">
						<button className="button button-outline" type="button" onClick={onClose}>
							Cancel
						</button>
						<button className="button button-primary" type="submit" disabled={busy || total > 100}>
							{busy ? "Saving…" : "Save draft definition"}
							<Icon name="arrow" size={16} />
						</button>
					</div>
				</form>
			</section>
		</div>
	);
}
