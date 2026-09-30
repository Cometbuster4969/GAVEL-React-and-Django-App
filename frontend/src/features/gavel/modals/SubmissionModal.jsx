import { useState } from "react";
import { Icon } from "../components/ui.jsx";

export function SubmissionModal({ campaign, onClose, onSubmit, busy }) {
	const [caseId, setCaseId] = useState(campaign.testCases[0]?.id || "");
	const [modelA, setModelA] = useState("Aster-2.1");
	const [modelB, setModelB] = useState("Nimbus-3.0");
	const [outputA, setOutputA] = useState("");
	const [outputB, setOutputB] = useState("");
	const [error, setError] = useState("");
	const submit = async (event) => {
		event.preventDefault();
		try {
			await onSubmit(campaign, [
				{ caseId, modelName: modelA, output: outputA, idempotencyKey: `${campaign.id}:${caseId}:${modelA}:${crypto.randomUUID()}` },
				{ caseId, modelName: modelB, output: outputB, idempotencyKey: `${campaign.id}:${caseId}:${modelB}:${crypto.randomUUID()}` },
			]);
		} catch (failure) {
			setError(failure.message);
		}
	};
	return (
		<div className="modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
			<section className="modal-card modal-wide" role="dialog" aria-modal="true" aria-labelledby="submit-responses-title">
				<div className="modal-head">
					<span className="modal-mark">
						<Icon name="upload" size={19} />
					</span>
					<button className="icon-quiet" type="button" onClick={onClose} aria-label="Close dialog">
						<Icon name="close" size={19} />
					</button>
				</div>
				<span className="eyebrow">RESPONSE INGESTION · {campaign.name}</span>
				<h2 id="submit-responses-title">Compare two outputs.</h2>
				<p className="modal-copy">
					Responses enter the queue first. Processing validates them and creates blind reviewer assignments.
				</p>
				<form className="modal-form" onSubmit={submit}>
					<label htmlFor="submission-case">Test case</label>
					<select id="submission-case" value={caseId} onChange={(event) => setCaseId(event.target.value)}>
						{campaign.testCases.map((item) => (
							<option key={item.id} value={item.id}>
								{item.title}
							</option>
						))}
					</select>
					<div className="submission-input-grid">
						<div>
							<label htmlFor="model-a">System name A</label>
							<input id="model-a" value={modelA} required onChange={(event) => setModelA(event.target.value)} />
							<label htmlFor="output-a">Response A</label>
							<textarea
								id="output-a"
								rows={5}
								required
								minLength={3}
								value={outputA}
								onChange={(event) => setOutputA(event.target.value)}
								placeholder="Paste the first model response…"
							/>
						</div>
						<div>
							<label htmlFor="model-b">System name B</label>
							<input id="model-b" value={modelB} required onChange={(event) => setModelB(event.target.value)} />
							<label htmlFor="output-b">Response B</label>
							<textarea
								id="output-b"
								rows={5}
								required
								minLength={3}
								value={outputB}
								onChange={(event) => setOutputB(event.target.value)}
								placeholder="Paste the second model response…"
							/>
						</div>
					</div>
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
							{busy ? "Queuing…" : "Queue 2 responses"}
							<Icon name="arrow" size={16} />
						</button>
					</div>
				</form>
			</section>
		</div>
	);
}
