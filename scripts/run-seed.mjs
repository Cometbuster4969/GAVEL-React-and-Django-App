import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const python = join(root, ".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python");
if (!existsSync(python)) {
	console.error(`Python virtualenv interpreter not found: ${python}`);
	process.exit(1);
}
const result = spawnSync(python, ["scripts/seed.py"], {
	cwd: join(root, "backend"),
	stdio: "inherit",
	shell: false,
});
process.exit(result.status ?? 1);
