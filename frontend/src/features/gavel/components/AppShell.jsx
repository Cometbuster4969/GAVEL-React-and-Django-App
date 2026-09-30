import { useState } from "react";
import { Icon, Avatar, GavelMark } from "../components/ui.jsx";
import { NAV_ITEMS, ROLE_LABELS } from "../constants.js";

export function AppShell({ user, onLogout, children, activeTab, setActiveTab, campaigns, onNewCampaign, onSearch }) {
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
