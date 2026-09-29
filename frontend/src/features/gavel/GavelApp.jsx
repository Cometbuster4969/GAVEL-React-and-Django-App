import { useCallback, useEffect, useMemo, useState } from "react";
import { gavelApi } from "./gavel.api.js";
import { setToken } from "../../shared/api/client.js";

const NAV_ITEMS = [
	{ id: "overview", label: "Overview", icon: "grid", group: "WORKSPACE" },
	{ id: "campaigns", label: "Campaigns", icon: "layers", group: "WORKSPACE" },
	{ id: "reviews", label: "Blind review", icon: "compare", group: "QUALITY" },
	{ id: "adjudications", label: "Adjudication", icon: "scale", group: "QUALITY" },
	{ id: "analytics", label: "Results", icon: "chart", group: "INSIGHTS" },
	{ id: "activity", label: "Audit history", icon: "clock", group: "INSIGHTS" },
];

const DEMO_ACCOUNTS = [
	{ name: "Maya Chen", role: "Campaign owner", email: "maya.chen@gavel.test", color: "#b9dc91" },
	{ name: "Jordan Lee", role: "Reviewer", email: "jordan.lee@gavel.test", color: "#d2b8f2" },
	{ name: "Priya Shah", role: "Adjudicator", email: "priya.shah@gavel.test", color: "#f1c47c" },
	{ name: "Elena Park", role: "Administrator", email: "elena.park@gavel.test", color: "#92c6ce" },
];

const ROLE_LABELS = { administrator: "Administrator", owner: "Campaign owner", reviewer: "Reviewer", adjudicator: "Adjudicator" };

function Icon({ name, size = 18, strokeWidth = 1.8 }) {
	const paths = {
		grid: (
			<>
				<rect x="3" y="3" width="7" height="7" rx="1.2" />
				<rect x="14" y="3" width="7" height="7" rx="1.2" />
				<rect x="3" y="14" width="7" height="7" rx="1.2" />
				<rect x="14" y="14" width="7" height="7" rx="1.2" />
			</>
		),
		layers: (
			<>
				<path d="m12 3 9 5-9 5-9-5 9-5Z" />
				<path d="m3 12 9 5 9-5M3 16l9 5 9-5" />
			</>
		),
		compare: (
			<>
				<path d="M8 6H4V2M4 6a8 8 0 0 1 13.7-2.8L20 6" />
				<path d="M16 18h4v4m0-4a8 8 0 0 1-13.7 2.8L4 18" />
				<path d="M8 9h8M8 13h5" />
			</>
		),
		scale: (
			<>
				<path d="M12 3v18M5 7h14M7 7l-4 8h8L7 7ZM17 7l-4 8h8l-4-8ZM8 21h8" />
			</>
		),
		chart: (
			<>
				<path d="M3 3v18h18" />
				<path d="m7 14 4-4 3 3 6-7" />
				<path d="M16 6h4v4" />
			</>
		),
		clock: (
			<>
				<circle cx="12" cy="12" r="9" />
				<path d="M12 7v5l3 2" />
			</>
		),
		search: (
			<>
				<circle cx="10.8" cy="10.8" r="6.8" />
				<path d="m16 16 4.5 4.5" />
			</>
		),
		plus: (
			<>
				<path d="M12 5v14M5 12h14" />
			</>
		),
		arrow: (
			<>
				<path d="M5 12h14M13 6l6 6-6 6" />
			</>
		),
		chevron: <path d="m9 18 6-6-6-6" />,
		down: <path d="m7 10 5 5 5-5" />,
		check: <path d="m5 12 4 4L19 6" />,
		close: (
			<>
				<path d="m6 6 12 12M18 6 6 18" />
			</>
		),
		menu: (
			<>
				<path d="M4 6h16M4 12h16M4 18h16" />
			</>
		),
		shield: (
			<>
				<path d="M12 22s8-4 8-11V5l-8-3-8 3v6c0 7 8 11 8 11Z" />
				<path d="m9 12 2 2 4-4" />
			</>
		),
		spark: (
			<>
				<path d="m12 3 1.9 5.8L20 11l-6.1 2.2L12 19l-1.9-5.8L4 11l6.1-2.2L12 3Z" />
				<path d="m19 14 1.1 2.9L23 18l-2.9 1.1L19 22l-1.1-2.9L15 18l2.9-1.1L19 14Z" />
			</>
		),
		upload: (
			<>
				<path d="M12 16V4m0 0L7 9m5-5 5 5" />
				<path d="M5 14v5a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-5" />
			</>
		),
		retry: (
			<>
				<path d="M20 7v5h-5M4 17v-5h5" />
				<path d="M5.6 9A7 7 0 0 1 17 5l3 2M4 17l3 2a7 7 0 0 0 11.4-4" />
			</>
		),
		dot: <circle cx="12" cy="12" r="3" fill="currentColor" stroke="none" />,
	};
	return (
		<svg
			aria-hidden="true"
			width={size}
			height={size}
			viewBox="0 0 24 24"
			fill="none"
			stroke="currentColor"
			strokeWidth={strokeWidth}
			strokeLinecap="round"
			strokeLinejoin="round"
		>
			{paths[name] || paths.dot}
		</svg>
	);
}

function Avatar({ user, size = "md" }) {
	const initials = (user?.name || "G")
		.split(" ")
		.map((part) => part[0])
		.slice(0, 2)
		.join("");
	return (
		<span className={`avatar avatar-${size}`} aria-hidden="true">
			{initials}
		</span>
	);
}

function StatusPill({ status }) {
	const labels = {
		processing: "Processing",
		draft: "Draft",
		published: "Published",
		running: "Running",
		reviewing: "In review",
		completed: "Completed",
		archived: "Archived",
		queued: "Queued",
		ready: "Processed",
		failed: "Failed",
		available: "Available",
		claimed: "Claimed",
		completedReview: "Complete",
		open: "Needs decision",
		resolved: "Resolved",
	};
	return <span className={`status-pill status-${status}`}>{labels[status] || status}</span>;
}

function LoginScreen({ onLogin }) {
	const [email, setEmail] = useState(DEMO_ACCOUNTS[0].email);
	const [password, setPassword] = useState("gavel2026!");
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState("");
	const signIn = async (event) => {
		event.preventDefault();
		setLoading(true);
		setError("");
		try {
			await onLogin(email.trim(), password);
		} catch (failure) {
			setError(failure.message);
		} finally {
			setLoading(false);
		}
	};
	return (
		<main className="login-screen">
			<div className="login-left">
				<div className="login-brand">
					<GavelMark />
					<span>
						gavel<span className="brand-period">.</span>
					</span>
				</div>
				<div className="login-story">
					<span className="eyebrow eyebrow-light">EVALUATION OPERATIONS</span>
					<h1>
						Make every model decision <em>defensible.</em>
					</h1>
					<p>Run structured evaluations, surface disagreement, and give your team the evidence to ship with confidence.</p>
					<div className="login-proof">
						<div className="proof-avatars">
							<i>MC</i>
							<i>JL</i>
							<i>PS</i>
							<i>+4</i>
						</div>
						<span>Trusted by teams building with AI</span>
					</div>
				</div>
				<div className="login-left-foot">
					<span>Private evaluation workspace</span>
					<span>01 / 04</span>
				</div>
			</div>
			<section className="login-panel">
				<div className="login-panel-top">
					<span>Welcome back</span>
					<span className="secure-label">
						<Icon name="shield" size={15} /> Secure workspace
					</span>
				</div>
				<div className="login-form-wrap">
					<span className="eyebrow">SIGN IN TO GAVEL</span>
					<h2>
						Your evaluation hub
						<br />
						is waiting.
					</h2>
					<p className="login-helper">Choose a demo role or enter your workspace credentials.</p>
					<div className="demo-users" role="group" aria-label="Demo profiles">
						{DEMO_ACCOUNTS.map((person) => (
							<button
								type="button"
								className={`demo-user ${email === person.email ? "selected" : ""}`}
								key={person.email}
								onClick={() => setEmail(person.email)}
								title={`Sign in as ${person.role}`}
							>
								<span style={{ "--avatar-color": person.color }}>
									{person.name
										.split(" ")
										.map((part) => part[0])
										.join("")}
								</span>
							</button>
						))}
					</div>
					<form onSubmit={signIn} className="login-form">
						<label htmlFor="login-email">Work email</label>
						<input
							autoComplete="username"
							id="login-email"
							type="email"
							value={email}
							required
							onChange={(event) => setEmail(event.target.value)}
						/>
						<div className="password-label">
							<label htmlFor="login-password">Password</label>
							<span>Demo: gavel2026!</span>
						</div>
						<input
							autoComplete="current-password"
							id="login-password"
							type="password"
							value={password}
							required
							onChange={(event) => setPassword(event.target.value)}
						/>
						{error && (
							<p className="form-error" role="alert">
								{error}
							</p>
						)}
						<button className="button button-primary button-full" type="submit" disabled={loading}>
							{loading ? "Signing in…" : "Continue to workspace"}
							<Icon name="arrow" size={17} />
						</button>
					</form>
					<p className="login-legal">By continuing, you agree to the workspace terms and privacy policy.</p>
				</div>
				<footer className="login-panel-foot">
					<span>© 2026 Gavel Evaluation Systems</span>
					<span>Help center&nbsp; · &nbsp;Privacy</span>
				</footer>
			</section>
		</main>
	);
}

function GavelMark() {
	return (
		<span className="gavel-mark">
			<svg aria-hidden="true" viewBox="0 0 32 32" fill="none">
				<path d="m9 8 4-4 9 9-4 4-9-9Z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
				<path d="m5 12 4-4m8 13 8-8M19 18l5 5m-9-1h13M8 20l4-4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
			</svg>
		</span>
	);
}

function AppShell({ user, onLogout, children, activeTab, setActiveTab, campaigns, onNewCampaign, onSearch }) {
	const [menuOpen, setMenuOpen] = useState(false);
	const [headerMenuOpen, setHeaderMenuOpen] = useState(false);
	const liveCampaign = campaigns.find((item) => item.status === "reviewing") || campaigns.find((item) => item.status === "running");
	const progressPercent = liveCampaign
		? Math.min(100, Math.round((liveCampaign.reviewCount / Math.max(1, liveCampaign.submissionCount)) * 100))
		: 0;
	const items = NAV_ITEMS.filter((item) => item.id !== "reviews" || ["reviewer", "administrator"].includes(user.role))
		.filter((item) => item.id !== "campaigns" || ["owner", "administrator"].includes(user.role))
		.filter((item) => item.id !== "adjudications" || ["adjudicator", "administrator", "owner"].includes(user.role))
		.filter((item) => item.id !== "activity" || user.role !== "reviewer")
		.filter((item) => item.id !== "analytics" || user.role !== "reviewer");
	return (
		<div className="app-shell">
			<aside className="sidebar" aria-label="Workspace navigation">
				<div className="sidebar-brand">
					<GavelMark />
					<span>
						gavel<span className="brand-period">.</span>
					</span>
					<span className="workspace-tag">OPS</span>
				</div>
				<div className="workspace-switcher" role="group" aria-label="Current workspace">
					<span className="workspace-monogram">N</span>
					<span className="workspace-copy">
						<strong>Northstar AI</strong>
						<small>Evaluation workspace</small>
					</span>
					<Icon name="down" size={15} />
				</div>
				<nav className="side-nav" aria-label="Main navigation">
					{items.map((item, index) => (
						<div key={item.id}>
							{(index === 0 || items[index - 1].group !== item.group) && <p className="nav-group-label">{item.group}</p>}
							<button
								className={`nav-item ${activeTab === item.id ? "active" : ""}`}
								type="button"
								onClick={() => setActiveTab(item.id)}
							>
								<Icon name={item.icon} />
								<span>{item.label}</span>
								{item.id === "adjudications" && campaigns.some((row) => row.status === "reviewing") && (
									<i className="nav-indicator" />
								)}
							</button>
						</div>
					))}
				</nav>
				<div className="sidebar-bottom">
					<div className="sidebar-active-card">
						<div className="active-card-top">
							<span className="live-dot" /> LIVE CAMPAIGN{" "}
							<button
								type="button"
								aria-label="Open campaigns"
								onClick={() => setActiveTab(["reviewer"].includes(user.role) ? "reviews" : "campaigns")}
							>
								<Icon name="arrow" size={14} />
							</button>
						</div>
						<strong>{liveCampaign?.name || "No active campaign"}</strong>
						<div className="mini-progress">
							<span style={{ width: `${progressPercent}%` }} />
						</div>
						<small>Evaluation in progress</small>
					</div>
					<button
						className="sidebar-help"
						type="button"
						onClick={() => setActiveTab(user.role === "reviewer" ? "reviews" : "activity")}
					>
						<span className="help-mark">?</span>
						<span>
							<strong>Need a hand?</strong>
							<small>View workspace activity</small>
						</span>
						<Icon name="chevron" size={15} />
					</button>
				</div>
				<div className="sidebar-user">
					<Avatar user={user} />
					<div className="sidebar-user-copy">
						<strong>{user.name}</strong>
						<span>{ROLE_LABELS[user.role]}</span>
					</div>
					<div className="profile-anchor">
						<button
							type="button"
							className="icon-quiet"
							aria-label="Open user menu"
							aria-expanded={menuOpen}
							onClick={() => setMenuOpen((value) => !value)}
						>
							<Icon name="down" size={16} />
						</button>
						{menuOpen && (
							<div className="profile-popover">
								<strong>{user.email}</strong>
								<span>{ROLE_LABELS[user.role]}</span>
								<button type="button" onClick={onLogout}>
									Sign out
								</button>
							</div>
						)}
					</div>
				</div>
			</aside>
			<main className="main-area">
				<header className="topbar">
					<div className="breadcrumbs">
						<span>Gavel</span>
						<Icon name="chevron" size={14} />
						<strong>{NAV_ITEMS.find((item) => item.id === activeTab)?.label || "Overview"}</strong>
					</div>
					<div className="topbar-actions">
						<label className="global-search">
							<Icon name="search" size={17} />
							<input
								placeholder="Search campaigns"
								aria-label="Search campaigns"
								onChange={(event) => onSearch(event.target.value)}
							/>
							<kbd>⌘ K</kbd>
						</label>
						<button
							className="topbar-icon"
							type="button"
							onClick={() => setActiveTab(user.role === "reviewer" ? "reviews" : "activity")}
							aria-label="View activity"
						>
							<Icon name="clock" size={17} />
						</button>
						<div className="topbar-user-anchor">
							<button
								className="topbar-avatar"
								type="button"
								aria-label="Open user menu"
								aria-expanded={headerMenuOpen}
								onClick={() => setHeaderMenuOpen((value) => !value)}
							>
								<Avatar user={user} size="sm" />
							</button>
							{headerMenuOpen && (
								<div className="profile-popover">
									<strong>{user.email}</strong>
									<span>{ROLE_LABELS[user.role]}</span>
									<button type="button" onClick={onLogout}>
										Sign out
									</button>
								</div>
							)}
						</div>
						{["administrator", "owner"].includes(user.role) && (
							<button className="topbar-new button button-primary" type="button" onClick={onNewCampaign}>
								<Icon name="plus" size={16} />
								<span>New evaluation</span>
							</button>
						)}
					</div>
				</header>
				{children}
			</main>
		</div>
	);
}

function PageHeading({ eyebrow, title, description, action }) {
	return (
		<div className="page-heading">
			<div>
				<span className="eyebrow">{eyebrow}</span>
				<h1>{title}</h1>
				<p>{description}</p>
			</div>
			{action}
		</div>
	);
}

function StatCard({ label, value, trend, icon, tone, foot }) {
	return (
		<article className="stat-card">
			<div className="stat-card-head">
				<span>{label}</span>
				<i className={`stat-icon ${tone}`}>
					<Icon name={icon} size={18} />
				</i>
			</div>
			<div className="stat-card-value">{value}</div>
			<div className="stat-card-foot">
				{trend && (
					<span className="trend-up">
						<Icon name="arrow" size={13} />
						{trend}
					</span>
				)}
				<span>{foot}</span>
			</div>
		</article>
	);
}

function OverviewPage({ user, campaigns, analytics, reviews, adjudications, onSelectCampaign, setActiveTab, onNewCampaign, search, busy }) {
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

function CampaignTable({ campaigns, onSelect }) {
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
							<td>
								<span className={`campaign-color campaign-color-${index % 4}`} />
								<span className="table-campaign-name">
									<strong>{item.name}</strong>
									<small>
										{item.testCaseCount} test cases · v{item.suiteVersion} suite
									</small>
								</span>
							</td>
							<td>
								<StatusPill status={item.status} />
							</td>
							<td>
								<strong className="response-number">{item.submissionCount}</strong>
								<small className="response-caption">{item.queuedCount ? `${item.queuedCount} queued` : "responses"}</small>
							</td>
							<td>
								<div className="table-progress">
									<span
										style={{
											width: `${item.submissionCount ? Math.min(100, Math.round((item.reviewCount / Math.max(1, item.submissionCount)) * 100)) : 0}%`,
										}}
									/>
								</div>
								<small className="progress-caption">{item.reviewCount} reviews</small>
							</td>
							<td>
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

function CampaignsPage({ campaigns, onSelect, onNewCampaign, search, onRefresh, loading }) {
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

function CampaignDetail({
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
	const failed = submissions.filter((item) => item.status === "failed").length;
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

function ReviewPage({ reviews, loading, activeReviewId, onSelect, onClaim, onRelease, onSubmit, busy }) {
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

function QueueSection({ title, items, activeId, onSelect }) {
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

function AdjudicationPage({ items, loading, onResolve, busy, canResolve }) {
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

function AnalyticsPage({ analytics, campaigns, loading }) {
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

function ActivityPage({ events, loading }) {
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

function CampaignModal({ onClose, onCreate, busy }) {
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

function CampaignEditorModal({ campaign, onClose, onSave, busy }) {
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

function SubmissionModal({ campaign, onClose, onSubmit, busy }) {
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

function formatRelative(value) {
	if (!value) return "just now";
	const seconds = Math.max(0, Math.floor((Date.now() - new Date(value).getTime()) / 1000));
	if (seconds < 60) return "just now";
	if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
	if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
	return `${Math.floor(seconds / 86400)}d ago`;
}

export default function App() {
	const [user, setUser] = useState(null);
	const [booting, setBooting] = useState(true);
	const [campaigns, setCampaigns] = useState([]);
	const [analytics, setAnalytics] = useState(null);
	const [reviews, setReviews] = useState([]);
	const [adjudications, setAdjudications] = useState([]);
	const [auditEvents, setAuditEvents] = useState([]);
	const [activeTab, setActiveTab] = useState("overview");
	const [selectedCampaign, setSelectedCampaign] = useState(null);
	const [selectedReviewId, setSelectedReviewId] = useState("");
	const [submissions, setSubmissions] = useState([]);
	const [search, setSearch] = useState("");
	const [modal, setModal] = useState("");
	const [busy, setBusy] = useState(false);
	const [loading, setLoading] = useState(false);
	const [submissionsLoading, setSubmissionsLoading] = useState(false);
	const [error, setError] = useState("");
	const [notice, setNotice] = useState("");

	const loadWorkspace = useCallback(async (actor) => {
		setLoading(true);
		const tasks = [gavelApi.campaigns(), actor.role === "reviewer" ? Promise.resolve(null) : gavelApi.analytics()];
		if (["reviewer", "administrator"].includes(actor.role)) tasks.push(gavelApi.reviews());
		else tasks.push(Promise.resolve([]));
		if (["administrator", "adjudicator", "owner"].includes(actor.role)) tasks.push(gavelApi.adjudications());
		else tasks.push(Promise.resolve([]));
		if (actor.role !== "reviewer") tasks.push(gavelApi.audit());
		else tasks.push(Promise.resolve([]));
		const results = await Promise.allSettled(tasks);
		const values = results.map((item) => (item.status === "fulfilled" ? item.value : null));
		if (results[0].status === "rejected") setError(results[0].reason.message);
		else setCampaigns(values[0]?.items || values[0] || []);
		setAnalytics(values[1]);
		setReviews(values[2]?.items || values[2] || []);
		setAdjudications(values[3]?.items || values[3] || []);
		setAuditEvents(values[4]?.items || values[4] || []);
		if (results.slice(1).some((item) => item.status === "rejected")) {
			const first = results.slice(1).find((item) => item.status === "rejected");
			if (first) setError(first.reason.message);
		}
		setLoading(false);
	}, []);

	useEffect(() => {
		let active = true;
		const token = localStorage.getItem("gavel-token");
		if (!token) {
			setBooting(false);
			return () => {
				active = false;
			};
		}
		gavelApi
			.me()
			.then((result) => {
				if (active) setUser(result.user);
			})
			.catch(() => {
				setToken("");
			})
			.finally(() => {
				if (active) setBooting(false);
			});
		return () => {
			active = false;
		};
	}, []);

	useEffect(() => {
		if (!user) return;
		loadWorkspace(user);
	}, [loadWorkspace, user?.id]);

	useEffect(() => {
		const handleSearchShortcut = (event) => {
			if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
				event.preventDefault();
				document.querySelector(".global-search input")?.focus();
			}
		};
		window.addEventListener("keydown", handleSearchShortcut);
		return () => window.removeEventListener("keydown", handleSearchShortcut);
	}, []);

	useEffect(() => {
		const handleExpired = (event) => {
			setUser(null);
			setError(event.detail || "Your session expired. Please sign in again.");
		};
		window.addEventListener("gavel-session-expired", handleExpired);
		return () => window.removeEventListener("gavel-session-expired", handleExpired);
	}, []);

	useEffect(() => {
		if (notice) {
			const timer = window.setTimeout(() => setNotice(""), 4200);
			return () => window.clearTimeout(timer);
		}
	}, [notice]);

	const refresh = async () => {
		if (user) {
			setError("");
			await loadWorkspace(user);
		}
	};
	const login = async (email, password) => {
		const result = await gavelApi.login(email, password);
		setToken(result.token);
		setUser(result.user);
		setActiveTab("overview");
		setError("");
	};
	const logout = () => {
		setToken("");
		setUser(null);
		setCampaigns([]);
		setReviews([]);
		setSelectedCampaign(null);
	};
	const chooseCampaign = async (campaign) => {
		setSelectedCampaign(campaign);
		setActiveTab("campaign-detail");
		setSubmissionsLoading(true);
		try {
			setSubmissions(await gavelApi.submissions(campaign.id));
		} catch (failure) {
			setSubmissions([]);
			setError(failure.message);
		} finally {
			setSubmissionsLoading(false);
		}
	};
	const runTransition = async (campaign, status) => {
		setBusy(true);
		setError("");
		try {
			const updated = await gavelApi.transition(campaign.id, status);
			setNotice(
				`Campaign ${status === "published" ? "published" : status === "running" ? "started" : status === "archived" ? "archived" : "updated"}.`,
			);
			await refresh();
			setSelectedCampaign(updated);
		} catch (failure) {
			setError(failure.message);
		} finally {
			setBusy(false);
		}
	};
	const publishResults = async (campaign) => {
		setBusy(true);
		setError("");
		try {
			await gavelApi.publishResults(campaign.id);
			setNotice("Immutable results snapshot published.");
			await refresh();
		} catch (failure) {
			setError(failure.message);
		} finally {
			setBusy(false);
		}
	};
	const createCampaignVersion = async (campaign) => {
		setBusy(true);
		setError("");
		try {
			const created = await gavelApi.createCampaignVersion(campaign.id);
			setSelectedCampaign(created);
			setActiveTab("campaign-detail");
			setNotice("New draft version created from the frozen campaign.");
			await refresh();
		} catch (failure) {
			setError(failure.message);
		} finally {
			setBusy(false);
		}
	};
	const createCampaign = async (payload) => {
		setBusy(true);
		try {
			const created = await gavelApi.createCampaign(payload);
			setModal("");
			setNotice("Draft evaluation created.");
			await refresh();
			setSelectedCampaign(created);
			setActiveTab("campaign-detail");
		} finally {
			setBusy(false);
		}
	};
	const submitResponses = async (campaign, items) => {
		setBusy(true);
		try {
			await gavelApi.ingest(campaign.id, items);
			setModal("");
			setNotice("Two responses added to the processing queue.");
			setSubmissions(await gavelApi.submissions(campaign.id));
			await refresh();
		} finally {
			setBusy(false);
		}
	};
	const processQueue = async (campaign) => {
		setBusy(true);
		setError("");
		try {
			const result = await gavelApi.process(campaign.id);
			setNotice(
				`${result.processed} response${result.processed === 1 ? "" : "s"} processed. ${result.reviewAssignmentsCreated} blind review assignments created.`,
			);
			setSubmissions(await gavelApi.submissions(campaign.id));
			await refresh();
			const updated = (await gavelApi.campaigns()).find((item) => item.id === campaign.id);
			if (updated) setSelectedCampaign(updated);
		} catch (failure) {
			setError(failure.message);
		} finally {
			setBusy(false);
		}
	};
	const retrySubmission = async (campaign, item) => {
		setBusy(true);
		try {
			await gavelApi.retry(campaign.id, item.id);
			setSubmissions(await gavelApi.submissions(campaign.id));
			setNotice("Response returned to the processing queue.");
			await refresh();
		} catch (failure) {
			setError(failure.message);
		} finally {
			setBusy(false);
		}
	};
	const deleteCampaign = async (campaign) => {
		setBusy(true);
		try {
			await gavelApi.deleteCampaign(campaign.id);
			setSelectedCampaign(null);
			setActiveTab("campaigns");
			setNotice("Draft campaign deleted. The audit record was retained.");
			await refresh();
		} catch (failure) {
			setError(failure.message);
		} finally {
			setBusy(false);
		}
	};
	const claimReview = async (review) => {
		// ponytail: optimistic claim with rollback on 409 conflict
		const prev = reviews;
		setReviews((current) =>
			current.map((r) => (r.id === review.id ? { ...r, status: "claimed", claimedByMe: true, claimedBy: "You" } : r)),
		);
		setBusy(true);
		setError("");
		try {
			const claimed = await gavelApi.claimReview(review.id);
			setSelectedReviewId(claimed.id);
			await refresh();
			setNotice("Review assignment claimed. Compare responses A and B.");
		} catch (failure) {
			setReviews(prev);
			await refresh();
			setError(failure.message);
		} finally {
			setBusy(false);
		}
	};
	const releaseReview = async (review) => {
		// ponytail: optimistic release with rollback
		const prev = reviews;
		setReviews((current) =>
			current.map((r) => (r.id === review.id ? { ...r, status: "available", claimedByMe: false, claimedBy: null } : r)),
		);
		setBusy(true);
		setError("");
		try {
			await gavelApi.releaseReview(review.id);
			await refresh();
			setNotice("Review assignment released back to the shared queue.");
		} catch (failure) {
			setReviews(prev);
			await refresh();
			setError(failure.message);
		} finally {
			setBusy(false);
		}
	};
	const submitReview = async (review, choice, notes, criterionScores) => {
		setBusy(true);
		setError("");
		try {
			const result = await gavelApi.submitReview(review.id, {
				choice,
				notes,
				criterionScores: Object.fromEntries(
					Object.entries(criterionScores).map(([id, scores]) => [id, { a: Number(scores.a), b: Number(scores.b) }]),
				),
			});
			setNotice(
				result.disagreementDetected
					? "Review submitted. A disagreement was sent to adjudication."
					: "Review submitted successfully.",
			);
			await refresh();
		} catch (failure) {
			setError(failure.message);
		} finally {
			setBusy(false);
		}
	};
	const resolveAdjudication = async (item, choice, rationale) => {
		setBusy(true);
		setError("");
		try {
			await gavelApi.resolveAdjudication(item.id, { choice, rationale });
			setNotice("Final decision recorded in the audit history.");
			await refresh();
		} catch (failure) {
			setError(failure.message);
		} finally {
			setBusy(false);
		}
	};

	const activeReviewId = useMemo(
		() =>
			reviews.some((item) => item.id === selectedReviewId)
				? selectedReviewId
				: reviews.find((item) => item.status === "claimed" && item.claimedByMe)?.id ||
					reviews.find((item) => item.status === "available")?.id ||
					reviews.find((item) => item.status === "completed")?.id ||
					"",
		[reviews, selectedReviewId],
	);

	if (booting)
		return (
			<div className="boot-screen">
				<GavelMark />
				<span>Preparing your workspace…</span>
			</div>
		);
	if (!user)
		return (
			<>
				<LoginScreen onLogin={login} />
				{error && (
					<div className="login-toast" role="alert">
						{error}
					</div>
				)}
			</>
		);

	return (
		<>
			<AppShell
				user={user}
				onLogout={logout}
				activeTab={activeTab}
				setActiveTab={setActiveTab}
				campaigns={campaigns}
				onNewCampaign={() => setModal("campaign")}
				onSearch={setSearch}
			>
				{error && (
					<div className="global-alert" role="alert">
						<Icon name="dot" size={16} />
						<span>{error}</span>
						<button type="button" onClick={() => setError("")} aria-label="Dismiss error">
							<Icon name="close" size={16} />
						</button>
					</div>
				)}
				{activeTab === "overview" && (
					<OverviewPage
						user={user}
						campaigns={campaigns}
						analytics={analytics}
						reviews={reviews}
						adjudications={adjudications}
						onSelectCampaign={["owner", "administrator"].includes(user.role) ? chooseCampaign : null}
						setActiveTab={setActiveTab}
						onNewCampaign={() => setModal("campaign")}
						search={search}
						busy={loading}
					/>
				)}
				{activeTab === "campaigns" && (
					<CampaignsPage
						campaigns={campaigns}
						onSelect={chooseCampaign}
						onNewCampaign={() => setModal("campaign")}
						search={search}
						onRefresh={refresh}
						loading={loading}
					/>
				)}
				{activeTab === "campaign-detail" && selectedCampaign && (
					<CampaignDetail
						campaign={campaigns.find((item) => item.id === selectedCampaign.id) || selectedCampaign}
						submissions={submissions}
						submissionsLoading={submissionsLoading}
						user={user}
						onTransition={runTransition}
						onPublishResults={publishResults}
						onCreateVersion={createCampaignVersion}
						onOpenSubmissions={() => setModal("submissions")}
						onProcess={processQueue}
						onRetry={retrySubmission}
						onEditDraft={() => setModal("edit-campaign")}
						onDelete={() => {
							if (window.confirm(`Delete the draft “${selectedCampaign.name}”? This cannot be undone.`))
								deleteCampaign(selectedCampaign);
						}}
						onBack={() => setActiveTab("campaigns")}
						busy={busy}
					/>
				)}
				{activeTab === "reviews" && (
					<ReviewPage
						reviews={reviews}
						loading={loading}
						activeReviewId={activeReviewId}
						onSelect={(review) => setSelectedReviewId(review.id)}
						onClaim={claimReview}
						onRelease={releaseReview}
						onSubmit={submitReview}
						busy={busy}
					/>
				)}
				{activeTab === "adjudications" && (
					<AdjudicationPage
						items={adjudications}
						loading={loading}
						onResolve={resolveAdjudication}
						busy={busy}
						canResolve={["administrator", "adjudicator"].includes(user.role)}
					/>
				)}
				{activeTab === "analytics" && <AnalyticsPage analytics={analytics} campaigns={campaigns} loading={loading} />}
				{activeTab === "activity" && <ActivityPage events={auditEvents} loading={loading} />}
				{notice && (
					<div className="toast-success" role="status">
						<span>
							<Icon name="check" size={16} />
						</span>
						{notice}
						<button type="button" onClick={() => setNotice("")} aria-label="Dismiss notification">
							<Icon name="close" size={15} />
						</button>
					</div>
				)}
			</AppShell>
			{modal === "campaign" && <CampaignModal onClose={() => setModal("")} onCreate={createCampaign} busy={busy} />}
			{modal === "edit-campaign" && selectedCampaign && (
				<CampaignEditorModal
					campaign={selectedCampaign}
					onClose={() => setModal("")}
					onSave={async (payload) => {
						setBusy(true);
						try {
							const updated = await gavelApi.updateCampaign(selectedCampaign.id, payload);
							setSelectedCampaign(updated);
							setModal("");
							setNotice("Draft suite and rubric updated.");
							await refresh();
						} finally {
							setBusy(false);
						}
					}}
					busy={busy}
				/>
			)}
			{modal === "submissions" && selectedCampaign && (
				<SubmissionModal campaign={selectedCampaign} onClose={() => setModal("")} onSubmit={submitResponses} busy={busy} />
			)}
		</>
	);
}
