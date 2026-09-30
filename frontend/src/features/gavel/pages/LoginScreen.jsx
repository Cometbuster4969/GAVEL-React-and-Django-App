import { useState } from "react";
import { Icon, GavelMark } from "../components/ui.jsx";
import { DEMO_ACCOUNTS } from "../constants.js";

export function LoginScreen({ onLogin }) {
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
