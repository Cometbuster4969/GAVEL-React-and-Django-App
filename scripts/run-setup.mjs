import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";

const bashCandidates = process.platform === "win32"
	? ["C:\\Program Files\\Git\\bin\\bash.exe", "C:\\Program Files\\Git\\usr\\bin\\bash.exe"]
	: ["bash"];
const bash = bashCandidates.find((candidate) => existsSync(candidate)) || (process.platform !== "win32" ? "bash" : null);
if (!bash) {
	console.error("bash is required to run setup.sh");
	process.exit(1);
}
const result = spawnSync(bash, ["setup.sh", ...process.argv.slice(2)], { stdio: "inherit", shell: false });
process.exit(result.status ?? 1);
