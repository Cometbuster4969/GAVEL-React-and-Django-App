export function Icon({ name, size = 18, strokeWidth = 1.8 }) {
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

export function Avatar({ user, size = "md" }) {
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

export function StatusPill({ status }) {
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

export function GavelMark() {
	return (
		<span className="gavel-mark">
			<svg aria-hidden="true" viewBox="0 0 32 32" fill="none">
				<path d="m9 8 4-4 9 9-4 4-9-9Z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" />
				<path d="m5 12 4-4m8 13 8-8M19 18l5 5m-9-1h13M8 20l4-4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
			</svg>
		</span>
	);
}

export function PageHeading({ eyebrow, title, description, action }) {
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

export function StatCard({ label, value, trend, icon, tone, foot }) {
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
