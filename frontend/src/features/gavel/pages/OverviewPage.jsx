import { Icon, GavelMark, PageHeading, StatCard } from "../components/ui.jsx";
import { CampaignTable } from "./CampaignsPage.jsx";

export function OverviewPage({ user, campaigns, analytics, reviews, adjudications, onSelectCampaign, setActiveTab, onNewCampaign, search, busy }) {
	const active = campaigns.find((item) => item.status === "reviewing") || campaigns.find((item) => item.status === "running");
	const assignedCount = reviews.filter((item) => item.status === "available" || item.status === "claimed").length;
	const openCount = adjudications.filter((item) => item.status === "open").length;
	const roleReview = user.role === "reviewer";
	return (
		<div className="page-content">
			<PageHeading
				eyebrow={new Intl.DateTimeFormat("en-US", { weekday: "long", month: "long", day: "numeric" })
					.format(new Date())
					.toUpperCase()}
				title={`Good morning, ${user.name.split(" ")[0]}`}
				description="Here's the latest from your evaluation workspace."
				action={
					user.role === "owner" || user.role === "administrator" ? (
						<button className="button button-primary" type="button" onClick={onNewCampaign}>
							<Icon name="plus" size={17} />
							Create evaluation
						</button>
					) : null
				}
			/>
			<div className="overview-banner">
				<div className="banner-art" aria-hidden="true">
					<div className="orbit orbit-one" />
					<div className="orbit orbit-two" />
					<div className="banner-gavel">
						<GavelMark />
					</div>
					<span className="banner-star star-one">✦</span>
					<span className="banner-star star-two">✧</span>
				</div>
				<div className="banner-copy">
					<span className="banner-label">
						<i className="live-dot" />
						{active ? "CAMPAIGN IN PROGRESS" : "YOUR WORKSPACE"}
					</span>
					<h2>{active?.name || "Build confidence in your AI"}</h2>
					<p>{active?.summary || "Create your first evaluation campaign and bring your team together around quality."}</p>
					<button className="banner-link" type="button" onClick={() => (active ? onSelectCampaign(active) : onNewCampaign())}>
						{active ? "View campaign" : "Start an evaluation"}
						<Icon name="arrow" size={16} />
					</button>
				</div>
				<div className="banner-side-note">
					<span>RUBRIC VERSION</span>
					<strong>v{active?.rubricVersion || 1}.0</strong>
					<small>Frozen for blind review</small>
				</div>
			</div>
			<div className="stats-grid">
				<StatCard
					label="Evaluations"
					value={analytics?.campaigns ?? campaigns.length}
					foot="Across your workspace"
					icon="layers"
					tone="tone-lilac"
				/>
				<StatCard
					label="Responses processed"
					value={analytics?.processed ?? 0}
					foot={`${analytics?.queued ?? 0} waiting in queue`}
					icon="check"
					tone="tone-green"
				/>
				<StatCard
					label="Reviewer agreement"
					value={`${analytics?.agreementRate ?? 0}%`}
					foot="Across completed comparisons"
					icon="compare"
					tone="tone-blue"
				/>
				<StatCard
					label={roleReview ? "Your open tasks" : "Needs adjudication"}
					value={roleReview ? assignedCount : openCount}
					foot={roleReview ? "Blind comparisons in your queue" : "Disagreements awaiting a decision"}
					icon={roleReview ? "compare" : "scale"}
					tone="tone-orange"
				/>
			</div>
			<div className="dashboard-grid">
				<section className="panel campaign-panel">
					<div className="panel-heading">
						<div>
							<span className="eyebrow">WORKSPACE</span>
							<h2>Evaluation campaigns</h2>
						</div>
						<button className="text-button" type="button" onClick={() => setActiveTab("campaigns")}>
							View all <Icon name="arrow" size={15} />
						</button>
					</div>
					{busy && campaigns.length === 0 ? (
						<div className="empty-state">
							<span className="spinner" />
							Loading campaigns…
						</div>
					) : (
						<CampaignTable
							campaigns={campaigns.filter((item) => !search || item.name.toLowerCase().includes(search.toLowerCase()))}
							onSelect={onSelectCampaign}
						/>
					)}
				</section>
				<section className="panel attention-panel">
					<div className="panel-heading">
						<div>
							<span className="eyebrow">NEXT UP</span>
							<h2>Needs your attention</h2>
						</div>
						<span className="attention-count">{roleReview ? assignedCount : openCount}</span>
					</div>
					{roleReview ? (
						<div className="attention-item">
							<span className="attention-icon violet">
								<Icon name="compare" />
							</span>
							<div>
								<strong>
									{assignedCount
										? `${assignedCount} blind comparison${assignedCount > 1 ? "s" : ""} ready`
										: "You're all caught up"}
								</strong>
								<span>
									{assignedCount
										? "Reviewers can't see which model wrote each response."
										: "New assignments will show up here."}
								</span>
							</div>
							<button type="button" aria-label="Open blind review" onClick={() => setActiveTab("reviews")}>
								<Icon name="arrow" size={16} />
							</button>
						</div>
					) : (
						<div className="attention-item">
							<span className="attention-icon amber">
								<Icon name="scale" />
							</span>
							<div>
								<strong>
									{openCount
										? `${openCount} disagreement${openCount > 1 ? "s" : ""} to resolve`
										: "No open disagreements"}
								</strong>
								<span>
									{openCount ? "Two reviewers chose different responses." : "Your review queue is looking consistent."}
								</span>
							</div>
							<button type="button" aria-label="Open adjudication" onClick={() => setActiveTab("adjudications")}>
								<Icon name="arrow" size={16} />
							</button>
						</div>
					)}
					<div className="attention-divider" />
					<div className="attention-meta">
						<span className="avatar-stack">
							<i>MC</i>
							<i>JL</i>
							<i>PS</i>
						</span>
						<span>Team activity</span>
						<button type="button" onClick={() => setActiveTab(user.role === "reviewer" ? "reviews" : "activity")}>
							View log <Icon name="arrow" size={14} />
						</button>
					</div>
				</section>
			</div>
			<section className="panel workflow-panel">
				<div className="panel-heading">
					<div>
						<span className="eyebrow">HOW IT WORKS</span>
						<h2>From prompt to confident decision</h2>
					</div>
					<span className="workflow-caption">A connected quality loop</span>
				</div>
				<div className="workflow-steps">
					{[
						{ n: "01", title: "Build a campaign", copy: "Versioned test cases & rubric", icon: "layers", tone: "violet" },
						{ n: "02", title: "Run responses", copy: "Queue, validate & process", icon: "upload", tone: "blue" },
						{ n: "03", title: "Review blind", copy: "Pairwise, identity hidden", icon: "compare", tone: "green" },
						{ n: "04", title: "Decide & learn", copy: "Resolve, measure, repeat", icon: "chart", tone: "orange" },
					].map((step, index) => (
						<div className="workflow-step" key={step.n}>
							<span className={`workflow-icon ${step.tone}`}>
								<Icon name={step.icon} size={19} />
							</span>
							<div>
								<small>{step.n}</small>
								<strong>{step.title}</strong>
								<span>{step.copy}</span>
							</div>
							{index < 3 && <i className="workflow-connector" />}
						</div>
					))}
				</div>
			</section>
			<div className="page-footer">
				<span>Gavel Evaluation Operations</span>
				<span>
					System status <i className="healthy-dot" /> All services operational
				</span>
			</div>
		</div>
	);
}
