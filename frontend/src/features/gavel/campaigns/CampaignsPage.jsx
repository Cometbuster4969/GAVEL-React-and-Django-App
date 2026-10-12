import { Icon, StatusPill, PageHeading } from "../components/ui.jsx";
import { formatRelative } from "../format.js";

export function CampaignTable({ campaigns, onSelect }) {
	if (!campaigns.length)
		return (
			<div className="empty-inline">
				<span className="empty-icon">
					<Icon name="layers" size={22} />
				</span>
				<strong>No campaigns yet</strong>
				<span>Create an evaluation to get started.</span>
			</div>
		);
	return (
		<div className="campaign-table-wrap">
			<table className="campaign-table">
				<thead>
					<tr>
						<th>CAMPAIGN</th>
						<th>STATUS</th>
						<th>RESPONSES</th>
						<th>REVIEW PROGRESS</th>
						<th>
							<span className="visually-hidden">Actions</span>
						</th>
					</tr>
				</thead>
				<tbody>
					{campaigns.slice(0, 5).map((item, index) => (
						<tr
							key={item.id}
							className={!onSelect ? "read-only-row" : ""}
							onClick={() => onSelect?.(item)}
							tabIndex={onSelect ? "0" : "-1"}
							onKeyDown={(event) => event.key === "Enter" && onSelect?.(item)}
						>
							<td data-label="Campaign">
								<span className={`campaign-color campaign-color-${index % 4}`} />
								<span className="table-campaign-name">
									<strong>{item.name}</strong>
									<small>
										{item.testCaseCount} test cases · v{item.suiteVersion} suite
									</small>
								</span>
							</td>
							<td data-label="Status">
								<StatusPill status={item.status} />
							</td>
							<td data-label="Responses">
								<strong className="response-number">{item.submissionCount}</strong>
								<small className="response-caption">{item.queuedCount ? `${item.queuedCount} queued` : "responses"}</small>
							</td>
							<td data-label="Review progress">
								<div className="table-progress">
									<span
										style={{
											width: `${item.submissionCount ? Math.min(100, Math.round((item.reviewCount / Math.max(1, item.submissionCount)) * 100)) : 0}%`,
										}}
									/>
								</div>
								<small className="progress-caption">{item.reviewCount} reviews</small>
							</td>
							<td data-label="">
								{onSelect && (
									<button
										className="row-arrow"
										aria-label={`Open ${item.name}`}
										type="button"
										onClick={(event) => {
											event.stopPropagation();
											onSelect(item);
										}}
									>
										<Icon name="chevron" size={16} />
									</button>
								)}
							</td>
						</tr>
					))}
				</tbody>
			</table>
		</div>
	);
}

export function CampaignsPage({ campaigns, onSelect, onNewCampaign, search, onRefresh, loading }) {
	const filtered = campaigns.filter(
		(item) => !search || item.name.toLowerCase().includes(search.toLowerCase()) || item.status.includes(search.toLowerCase()),
	);
	return (
		<div className="page-content">
			<PageHeading
				eyebrow="EVALUATION LIBRARY"
				title="Campaigns"
				description="Manage test suites, versioned rubrics, and the full evaluation lifecycle."
				action={
					<button className="button button-primary" type="button" onClick={onNewCampaign}>
						<Icon name="plus" size={17} />
						New campaign
					</button>
				}
			/>
			<div className="campaign-toolbar">
				<div className="campaign-filters">
					<span className="filter-active">
						All campaigns <b>{filtered.length}</b>
					</span>
					<span>
						In progress <b>{campaigns.filter((item) => ["running", "reviewing"].includes(item.status)).length}</b>
					</span>
					<span>
						Drafts <b>{campaigns.filter((item) => item.status === "draft").length}</b>
					</span>
				</div>
				<button type="button" className="button button-outline" onClick={onRefresh}>
					<Icon name="retry" size={16} />
					Refresh
				</button>
			</div>
			{loading && !campaigns.length ? (
				<div className="empty-state">
					<span className="spinner" />
					Loading campaigns…
				</div>
			) : filtered.length ? (
				<div className="campaign-cards">
					{filtered.map((item, index) => (
						<button type="button" className="campaign-card" key={item.id} onClick={() => onSelect(item)}>
							<div className="campaign-card-top">
								<span className={`campaign-card-icon campaign-color-${index % 4}`}>
									<Icon name="layers" />
								</span>
								<StatusPill status={item.status} />
								<span className="card-more">
									<Icon name="chevron" size={17} />
								</span>
							</div>
							<h2>{item.name}</h2>
							<p>{item.summary}</p>
							<div className="campaign-card-meta">
								<span>
									<Icon name="grid" size={14} />
									{item.testCaseCount} test cases
								</span>
								<span>
									<Icon name="compare" size={14} />
									{item.reviewCount} reviews
								</span>
							</div>
							<div className="campaign-card-bottom">
								<span>
									Suite v{item.suiteVersion} <i>·</i> Rubric v{item.rubricVersion}
								</span>
								<small>Updated {formatRelative(item.updatedAt)}</small>
							</div>
						</button>
					))}
				</div>
			) : (
				<div className="panel empty-state">
					<span className="empty-icon">
						<Icon name="search" size={22} />
					</span>
					<strong>No campaigns match that search</strong>
					<span>Try another campaign name or status.</span>
				</div>
			)}
		</div>
	);
}
