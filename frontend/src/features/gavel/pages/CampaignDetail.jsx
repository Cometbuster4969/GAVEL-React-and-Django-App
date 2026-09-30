import { Icon, StatusPill } from "../components/ui.jsx";

export function CampaignDetail({
	campaign,
	submissions,
	submissionsLoading,
	user,
	onTransition,
	onPublishResults,
	onCreateVersion,
	onOpenSubmissions,
	onProcess,
	onRetry,
	onEditDraft,
	onDelete,
	onBack,
	busy,
}) {
	const actions = {
		draft: ["published", "Publish campaign"],
		published: ["running", "Start evaluation"],
		running: null,
		reviewing: ["completed", "Complete campaign"],
		completed: ["archived", "Archive campaign"],
		archived: null,
	};
	const action = actions[campaign.status];
	const canManage = ["administrator", "owner"].includes(user.role);
	const queued = submissions.filter((item) => item.status === "queued").length;
	return (
		<div className="page-content campaign-detail-page">
			<button type="button" className="back-link" onClick={onBack}>
				←&nbsp; All campaigns
			</button>
			<div className="detail-heading">
				<div>
					<span className="eyebrow">CAMPAIGN OVERVIEW · SUITE V{campaign.suiteVersion}</span>
					<h1>{campaign.name}</h1>
					<p>{campaign.summary}</p>
				</div>
				<StatusPill status={campaign.status} />
			</div>
			<div className="detail-stats">
				<div>
					<span>Test cases</span>
					<strong>{campaign.testCaseCount}</strong>
				</div>
				<div>
					<span>Responses</span>
					<strong>{campaign.submissionCount}</strong>
				</div>
				<div>
					<span>Reviews complete</span>
					<strong>{campaign.reviewCount}</strong>
				</div>
				<div>
					<span>Rubric version</span>
					<strong>v{campaign.rubricVersion}</strong>
				</div>
			</div>
			<div className="detail-actions">
				{action && canManage && (
					<button
						type="button"
						className="button button-primary"
						disabled={busy}
						onClick={() => onTransition(campaign, action[0])}
					>
						{busy ? "Updating…" : action[1]}
						<Icon name="arrow" size={16} />
					</button>
				)}
				{campaign.status === "draft" && canManage && (
					<button type="button" className="button button-outline" onClick={onEditDraft}>
						<Icon name="layers" size={16} />
						Edit suite & rubric
					</button>
				)}
				{campaign.status === "completed" && canManage && (
					<button type="button" className="button button-primary" disabled={busy} onClick={() => onPublishResults(campaign)}>
						<Icon name="chart" size={16} />
						{busy ? "Publishing…" : "Publish results"}
					</button>
				)}
				{campaign.status !== "draft" && campaign.status !== "archived" && canManage && (
					<button type="button" className="button button-outline" disabled={busy} onClick={() => onCreateVersion(campaign)}>
						<Icon name="layers" size={16} />
						Create new version
					</button>
				)}
				{campaign.status === "draft" && canManage && (
					<button type="button" className="button button-danger-outline" onClick={onDelete}>
						Delete draft
					</button>
				)}
				{campaign.status === "running" && canManage && (
					<button type="button" className="button button-primary" onClick={onOpenSubmissions}>
						<Icon name="plus" size={16} />
						Add responses
					</button>
				)}
				{campaign.status === "running" && canManage && (
					<button type="button" className="button button-outline" disabled={!queued || busy} onClick={() => onProcess(campaign)}>
						<Icon name="spark" size={16} />
						Process queue {queued > 0 && <b className="button-count">{queued}</b>}
					</button>
				)}
				<span className="detail-freeze">
					<Icon name="shield" size={15} />
					{campaign.status === "draft" ? "Definitions editable until publish" : "Test suite and rubric are version-frozen"}
				</span>
			</div>
			<div className="detail-columns">
				<section className="panel">
					<div className="panel-heading">
						<div>
							<span className="eyebrow">TEST SUITE · V{campaign.suiteVersion}</span>
							<h2>Evaluation prompts</h2>
						</div>
						<span className="small-count">{campaign.testCases.length} cases</span>
					</div>
					<div className="case-list">
						{campaign.testCases.map((testCase, index) => (
							<article className="case-card" key={testCase.id}>
								<span className="case-index">{String(index + 1).padStart(2, "0")}</span>
								<div>
									<strong>{testCase.title}</strong>
									<p>{testCase.prompt}</p>
									<small>{testCase.id}</small>
								</div>
							</article>
						))}
					</div>
				</section>
				<section className="panel rubric-panel">
					<div className="panel-heading">
						<div>
							<span className="eyebrow">SCORING FRAMEWORK · V{campaign.rubricVersion}</span>
							<h2>Weighted rubric</h2>
						</div>
						<span className="rubric-total">100%</span>
					</div>
					<div className="rubric-list">
						{campaign.rubric.map((criterion, index) => (
							<div className="rubric-row" key={criterion.id}>
								<span className={`rubric-marker marker-${index % 4}`} />
								<div>
									<strong>{criterion.title}</strong>
									<small>{criterion.description}</small>
								</div>
								<b>{criterion.weight}%</b>
							</div>
						))}
					</div>
					<div className="rubric-foot">
						<Icon name="shield" size={15} />
						Pinned to all reviews in this campaign
					</div>
				</section>
			</div>
			<section className="panel submission-panel">
				<div className="panel-heading">
					<div>
						<span className="eyebrow">RESPONSE PIPELINE</span>
						<h2>Submissions</h2>
					</div>
					<span className="small-count">{campaign.submissionCount} total</span>
				</div>
				{submissionsLoading ? (
					<div className="empty-state">
						<span className="spinner" />
						Loading submissions…
					</div>
				) : submissions.length ? (
					<div className="submission-table-wrap">
						<table className="submission-table">
							<thead>
								<tr>
									<th>MODEL</th>
									<th>TEST CASE</th>
									<th>STATE</th>
									<th>ATTEMPTS</th>
									<th>
										<span className="visually-hidden">Actions</span>
									</th>
								</tr>
							</thead>
							<tbody>
								{submissions.map((item) => (
									<tr key={item.id}>
										<td>
											<strong>{item.modelName}</strong>
											<small className="submission-truncate">{item.output}</small>
										</td>
										<td>{campaign.testCases.find((testCase) => testCase.id === item.caseId)?.title || item.caseId}</td>
										<td>
											<StatusPill status={item.status} />
											{item.failureReason && <small className="failure-copy">{item.failureReason}</small>}
										</td>
										<td>{item.attempt}/3</td>
										<td>
											{item.status === "failed" && canManage && (
												<button
													className="text-button"
													type="button"
													disabled={item.attempt >= 3}
													onClick={() => onRetry(campaign, item)}
												>
													Retry
												</button>
											)}
										</td>
									</tr>
								))}
							</tbody>
						</table>
					</div>
				) : (
					<div className="empty-inline">
						<span className="empty-icon">
							<Icon name="upload" size={22} />
						</span>
						<strong>No responses have been submitted</strong>
						<span>Start the campaign, then add model responses to the queue.</span>
					</div>
				)}
			</section>
		</div>
	);
}
