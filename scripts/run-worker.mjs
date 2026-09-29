import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const python = join(root, ".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
if (!existsSync(python)) {
	console.error(`Python virtualenv interpreter not found: ${python}`);
	process.exit(1);
}
// Extra arguments after `bun run worker` are forwarded to the worker entry point.
const child = spawn(python, ["-m", "apps.gavel.worker", ...process.argv.slice(2)], {
	cwd: join(root, "backend"),
	stdio: "inherit",
	shell: false,
});
child.on("exit", (code, signal) => process.exit(code ?? (signal ? 1 : 0)));
