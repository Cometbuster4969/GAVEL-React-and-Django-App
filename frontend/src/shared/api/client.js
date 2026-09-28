const baseUrl = import.meta.env.VITE_API_URL || "/api/v1";
let token = localStorage.getItem("gavel-token") || "";

export function setToken(value) {
	token = value || "";
	if (token) localStorage.setItem("gavel-token", token);
	else localStorage.removeItem("gavel-token");
}

export async function request(path, options = {}) {
	let response;
	try {
		response = await fetch(`${baseUrl}${path}`, {
			...options,
			headers: {
				"Content-Type": "application/json",
				...(token ? { Authorization: `Bearer ${token}` } : {}),
				...options.headers,
			},
		});
	} catch {
		throw new Error("Gavel could not reach the API. Check that the backend is running and try again.");
	}
	if (response.status === 204) return null;
	const payload = await response.json().catch(() => null);
	if (!response.ok) {
		const error = new Error(payload?.error?.message || `Gavel returned ${response.status}.`);
		error.status = response.status;
		error.code = payload?.error?.code;
		error.details = payload?.error?.details;
		if (response.status === 401 && token) {
			setToken("");
			window.dispatchEvent(new CustomEvent("gavel-session-expired", { detail: error.message }));
		}
		throw error;
	}
	if (!payload || !("data" in payload)) throw new Error("Gavel returned an invalid response.");
	return payload.data;
}
