import { useState, useEffect, useMemo, useCallback } from "react";
import { gavelApi } from "./gavel.api.js";
import { setToken } from "../../shared/api/client.js";
import { Icon, GavelMark } from "./components/ui.jsx";
import { AppShell } from "./components/AppShell.jsx";
import { LoginScreen } from "./auth/LoginScreen.jsx";
import { OverviewPage } from "./overview/OverviewPage.jsx";
import { CampaignsPage } from "./campaigns/CampaignsPage.jsx";
import { CampaignDetail } from "./campaigns/CampaignDetail.jsx";
import { ReviewPage } from "./reviews/ReviewPage.jsx";
import { AdjudicationPage } from "./adjudications/AdjudicationPage.jsx";
import { AnalyticsPage } from "./analytics/AnalyticsPage.jsx";
import { ActivityPage } from "./activity/ActivityPage.jsx";
import { CampaignModal } from "./campaigns/CampaignModal.jsx";
import { CampaignEditorModal } from "./campaigns/CampaignEditorModal.jsx";
import { SubmissionModal } from "./campaigns/SubmissionModal.jsx";

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
