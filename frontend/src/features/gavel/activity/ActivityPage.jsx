import { Icon, Avatar, PageHeading } from "../components/ui.jsx";
import { formatRelative } from "../format.js";

export function ActivityPage({ events, loading }) {
	const actionLabels = {
		"campaign.created": "created a campaign",
		"campaign.deleted": "deleted a draft campaign",
		"campaign.updated": "updated a campaign",
		"campaign.status_changed": "changed campaign status",
		"campaign.published": "published a campaign",
		"submissions.queued": "queued model responses",
		"submissions.processed": "processed a response batch",
		"reviews.generated": "created blind review assignments",
		"review.claimed": "claimed a blind review",
		"review.completed": "submitted a blind review",
		"disagreement.detected": "flagged a reviewer disagreement",
		"adjudication.resolved": "recorded an adjudication decision",
	};
	return (
		<div className="page-content">
			<PageHeading
				eyebrow="GOVERNANCE"
				title="Audit history"
				description="A permanent record of campaign changes, review decisions, and adjudication."
				action={
					<span className="audit-immutable">
						<Icon name="shield" size={15} />
						Append-only record
					</span>
				}
			/>
			{loading ? (
				<div className="panel empty-state">
					<span className="spinner" />
					Loading audit history…
				</div>
			) : events.length ? (
				<section className="panel audit-panel">
					<div className="audit-table-head">
						<span>ACTIVITY</span>
						<span>EVENT</span>
						<span>WHEN</span>
					</div>
					{events.map((event) => (
						<article className="audit-row" key={event.id}>
							<Avatar user={{ name: event.actor }} size="sm" />
							<div className="audit-actor">
								<strong>{event.actor}</strong>
								<span>{actionLabels[event.action] || event.action.replaceAll(".", " ")}</span>
							</div>
							<div className="audit-event">
								<span>{event.entityType}</span>
								<small>
									{event.details?.name || event.details?.to || event.details?.caseId || event.entityId.slice(-8)}
								</small>
							</div>
							<time>{formatRelative(event.createdAt)}</time>
						</article>
					))}
				</section>
			) : (
				<div className="panel empty-state">
					<span className="empty-icon">
						<Icon name="clock" size={22} />
					</span>
					<strong>No activity recorded</strong>
					<span>Workspace actions will appear here.</span>
				</div>
			)}
		</div>
	);
}
