import { request } from "../../shared/api/client.js";

const json = (value) => ({ method: "POST", body: JSON.stringify(value) });

export const gavelApi = {
	login: (email, password) => request("/auth/login", json({ email, password })),
	me: () => request("/auth/me"),
	campaigns: () => request("/campaigns"),
	createCampaign: (values) => request("/campaigns/create", json(values)),
	updateCampaign: (id, values) => request(`/campaigns/${id}`, { method: "PATCH", body: JSON.stringify(values) }),
	deleteCampaign: (id) => request(`/campaigns/${id}`, { method: "DELETE" }),
	transition: (id, status) => request(`/campaigns/${id}/transition`, json({ status })),
	submissions: (id) => request(`/campaigns/${id}/submissions`),
	ingest: (id, items) => request(`/campaigns/${id}/submissions`, json({ items })),
	process: (id) => request(`/campaigns/${id}/submissions/process`, json({ limit: 25 })),
	retry: (campaignId, submissionId) => request(`/campaigns/${campaignId}/submissions/${submissionId}/retry`, json({})),
	reviews: () => request("/reviews"),
	claimReview: (id) => request(`/reviews/${id}/claim`, json({})),
	releaseReview: (id) => request(`/reviews/${id}/release`, json({})),
	submitReview: (id, values) => request(`/reviews/${id}/submit`, json(values)),
	adjudications: () => request("/adjudications"),
	resolveAdjudication: (id, values) => request(`/adjudications/${id}/resolve`, json(values)),
	analytics: () => request("/analytics"),
	audit: () => request("/audit"),
};
