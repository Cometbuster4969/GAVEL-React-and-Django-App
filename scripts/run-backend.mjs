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
const child = spawn(python, ["manage.py", "runserver", "0.0.0.0:8000"], {
	cwd: join(root, "backend"),
	stdio: "inherit",
	shell: false,
});
child.on("exit", (code, signal) => process.exit(code ?? (signal ? 1 : 0)));
