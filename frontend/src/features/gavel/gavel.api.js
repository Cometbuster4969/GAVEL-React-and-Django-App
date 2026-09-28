import { request } from "../../shared/api/client.js";

const json = (value) => ({ method: "POST", body: JSON.stringify(value) });

export const gavelApi = {
	login: (email, password) => request("/auth/login", json({ email, password })),
	me: () => request("/auth/me"),
	campaigns: (params = {}) => {
		const qs = new URLSearchParams(params).toString();
		return request(`/campaigns${qs ? `?${qs}` : ""}`);
	},
	createCampaign: (values) => request("/campaigns/create", json(values)),
	createCampaignVersion: (id) => request(`/campaigns/${id}/versions`, json({})),
	updateCampaign: (id, values) => request(`/campaigns/${id}`, { method: "PATCH", body: JSON.stringify(values) }),
	deleteCampaign: (id) => request(`/campaigns/${id}`, { method: "DELETE" }),
	transition: (id, status) => request(`/campaigns/${id}/transition`, json({ status })),
	publishResults: (id) => request(`/campaigns/${id}/publish-results`, json({})),
	publishedResults: (id) => request(`/campaigns/${id}/published-results`),
	exportResults: (id, format = "json") => request(`/campaigns/${id}/results-export?format=${format}`),
	submissions: (id, params = {}) => {
		const qs = new URLSearchParams(params).toString();
		return request(`/campaigns/${id}/submissions${qs ? `?${qs}` : ""}`);
	},
	ingest: (id, items) => request(`/campaigns/${id}/submissions`, json({ items })),
	process: (id) => request(`/campaigns/${id}/submissions/process`, json({ limit: 25 })),
	retry: (campaignId, submissionId) => request(`/campaigns/${campaignId}/submissions/${submissionId}/retry`, json({})),
	reviews: (params = {}) => {
		const qs = new URLSearchParams(params).toString();
		return request(`/reviews${qs ? `?${qs}` : ""}`);
	},
	claimReview: (id) => request(`/reviews/${id}/claim`, json({})),
	releaseReview: (id) => request(`/reviews/${id}/release`, json({})),
	submitReview: (id, values) => request(`/reviews/${id}/submit`, json(values)),
	adjudications: (params = {}) => {
		const qs = new URLSearchParams(params).toString();
		return request(`/adjudications${qs ? `?${qs}` : ""}`);
	},
	resolveAdjudication: (id, values) => request(`/adjudications/${id}/resolve`, json(values)),
	analytics: (params = {}) => {
		const qs = new URLSearchParams(params).toString();
		return request(`/analytics${qs ? `?${qs}` : ""}`);
	},
	audit: (params = {}) => {
		const qs = new URLSearchParams(params).toString();
		return request(`/audit${qs ? `?${qs}` : ""}`);
	},
};
