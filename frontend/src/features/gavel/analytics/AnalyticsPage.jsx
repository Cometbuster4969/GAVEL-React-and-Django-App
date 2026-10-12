import { CampaignTable } from "../campaigns/CampaignsPage.jsx";
import { Icon, PageHeading, StatCard } from "../components/ui.jsx";

export function AnalyticsPage({ analytics, campaigns, loading }) {
	const maxWins = Math.max(1, ...(analytics?.modelWins || []).map((row) => row.wins));
	const campaignStats = analytics?.campaignBreakdown || [];
	return (
		<div className="page-content">
			<PageHeading
				eyebrow="EVALUATION INTELLIGENCE"
				title="Results & analytics"
				description="Track preference signals, reviewer consistency, and evaluation throughput."
				action={
					<button className="button button-outline" type="button" onClick={() => window.print()}>
						<Icon name="chart" size={16} />
						Export report
					</button>
				}
			/>
			{loading ? (
				<div className="panel empty-state">
					<span className="spinner" />
					Loading evaluation results…
				</div>
			) : (
				<>
					<div className="analytics-kpis">
						<StatCard
							label="Total responses"
							value={analytics?.submissions ?? 0}
							foot="Across all campaigns"
							icon="upload"
							tone="tone-blue"
						/>
						<StatCard
							label="Human comparisons"
							value={analytics?.reviewsCompleted ?? 0}
							foot={`${analytics?.reviewsPending ?? 0} still in queue`}
							icon="compare"
							tone="tone-lilac"
						/>
						<StatCard
							label="Reviewer agreement"
							value={`${analytics?.agreementRate ?? 0}%`}
							foot="Same preference across paired reviews"
							icon="check"
							tone="tone-green"
						/>
						<StatCard
							label="Disagreements"
							value={analytics?.resolvedDisagreements ?? 0}
							foot={`${analytics?.openDisagreements ?? 0} need adjudication`}
							icon="scale"
							tone="tone-orange"
						/>
					</div>
					<div className="analytics-grid">
						<section className="panel chart-panel">
							<div className="panel-heading">
								<div>
									<span className="eyebrow">QUALITY SIGNAL</span>
									<h2>Agreement by campaign</h2>
								</div>
								<span className="chart-range">
									All campaigns <Icon name="down" size={14} />
								</span>
							</div>
							<div className="chart-summary">
								<strong>{analytics?.agreementRate ?? 0}%</strong>
								<span>Average across completed paired reviews</span>
							</div>
							{campaignStats.length ? (
								<div className="bar-chart" role="group" aria-label="Reviewer agreement rate by campaign">
									{campaignStats.slice(0, 10).map((row, index) => (
										<div className="bar-col" key={row.id}>
											<span
												className={`bar ${index === 0 ? "bar-current" : ""}`}
												style={{ height: `${Math.max(4, row.agreementRate || 0)}%` }}
												title={`${row.name}: ${row.agreementRate}% agreement`}
											/>
											<small title={row.name}>{String(index + 1).padStart(2, "0")}</small>
										</div>
									))}
								</div>
							) : (
								<div className="empty-inline">
									<strong>No campaign data yet</strong>
									<span>Agreement rates appear when paired reviews are submitted.</span>
								</div>
							)}
							<div className="chart-legend">
								<span>
									<i />
									Reviewer agreement
								</span>
								<span>Based on stored campaign reviews</span>
							</div>
						</section>
						<section className="panel winners-panel">
							<div className="panel-heading">
								<div>
									<span className="eyebrow">PREFERENCE SIGNAL</span>
									<h2>Model wins</h2>
								</div>
								<Icon name="spark" size={18} />
							</div>
							{analytics?.modelWins?.length ? (
								<div className="model-win-list">
									{analytics.modelWins.map((row, index) => (
										<div className="model-win" key={row.model}>
											<div className="model-win-head">
												<span className={`model-dot model-dot-${index % 3}`} />
												<strong>{row.model}</strong>
												<b>{row.wins}</b>
											</div>
											<div className="model-win-track">
												<span style={{ width: `${Math.max(5, (row.wins / maxWins) * 100)}%` }} />
											</div>
										</div>
									))}
								</div>
							) : (
								<div className="empty-inline">
									<span className="empty-icon">
										<Icon name="chart" size={20} />
									</span>
									<strong>No preference results yet</strong>
									<span>Results appear after reviewers submit comparisons.</span>
								</div>
							)}
							<div className="winner-note">
								<Icon name="shield" size={15} />
								Votes are only revealed after blind review.
							</div>
						</section>
					</div>
					<section className="panel throughput-panel">
						<div className="panel-heading">
							<div>
								<span className="eyebrow">PROGRAM HEALTH</span>
								<h2>Campaign throughput</h2>
							</div>
							<span className="small-count">{campaigns.length} campaigns</span>
						</div>
						<CampaignTable campaigns={campaigns} onSelect={null} />
					</section>
				</>
			)}
		</div>
	);
}
