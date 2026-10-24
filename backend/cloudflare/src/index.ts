import { Container } from "@cloudflare/containers";

/**
 * Every setting the Django container needs. Each name must exist exactly once, either as a
 * secret (`wrangler secret bulk`, the default) or, for a value that is empty by design, as an
 * empty entry under "vars" in wrangler.jsonc (Cloudflare does not accept empty secrets).
 */
const SETTINGS = [
	"RESOLVE_AI_SECRET_KEY",
	"RESOLVE_AI_DB_PASSWORD",
	"RESOLVE_AI_REDIS_URL",
	"RESOLVE_AI_ENCRYPTION_KEYS",
	"RESOLVE_AI_GOOGLE_CLIENT_ID",
	"RESOLVE_AI_GOOGLE_CLIENT_SECRET",
	"RESOLVE_AI_GEMINI_API_KEY",
	"RESOLVE_AI_LLM_CALL_LIMIT",
	"RESOLVE_AI_R2_ACCESS_KEY_ID",
	"RESOLVE_AI_R2_SECRET_ACCESS_KEY",
	"RESOLVE_AI_DEBUG",
	"RESOLVE_AI_ENVIRONMENT",
	"RESOLVE_AI_USE_SQLITE",
	"RESOLVE_AI_RELAX_THROTTLES",
	"RESOLVE_AI_SECURE_COOKIES",
	"RESOLVE_AI_SSL_REDIRECT",
	"RESOLVE_AI_NUM_PROXIES",
	"RESOLVE_AI_COOKIE_DOMAIN",
	"RESOLVE_AI_ALLOWED_HOSTS",
	"RESOLVE_AI_FRONTEND_URL",
	"RESOLVE_AI_CORS_ALLOWED_ORIGINS",
	"RESOLVE_AI_CSRF_TRUSTED_ORIGINS",
	"RESOLVE_AI_PUBLIC_API_URL",
	"RESOLVE_AI_DB_HOST",
	"RESOLVE_AI_DB_PORT",
	"RESOLVE_AI_DB_NAME",
	"RESOLVE_AI_DB_USER",
	"RESOLVE_AI_DB_SSLMODE",
	"RESOLVE_AI_EMAIL_BACKEND",
	"RESOLVE_AI_DEFAULT_FROM_EMAIL",
	"RESOLVE_AI_SENTRY_DSN",
	"RESOLVE_AI_GMAIL_PUBSUB_TOPIC",
	"RESOLVE_AI_PUBSUB_PUSH_AUDIENCE",
	"RESOLVE_AI_PUBSUB_PUSH_SERVICE_ACCOUNT",
	"RESOLVE_AI_R2_ENDPOINT_URL",
	"RESOLVE_AI_R2_BUCKET_NAME",
	"RESOLVE_AI_R2_PUBLIC_BASE_URL",
] as const;

type SettingName = (typeof SETTINGS)[number];

interface Env extends Record<SettingName, string> {
	BACKEND: DurableObjectNamespace<BackendContainer>;
}

/** Values left over from secrets.example.json: they mean "someone forgot to fill this in". */
const PLACEHOLDERS = ["FILL_ME", "SUBDOMAIN"];

/**
 * Same rule as settings.py: a missing variable is an error, an empty one is fine. A value
 * that still holds a placeholder is an error too; the message names the variables, never
 * their values.
 */
function containerEnv(env: Env): Record<string, string> {
	const result: Record<string, string> = {};
	const missing: string[] = [];
	const placeholders: string[] = [];
	for (const name of SETTINGS) {
		const value = env[name];
		if (value === undefined) {
			missing.push(name);
			continue;
		}
		if (PLACEHOLDERS.some((placeholder) => value.includes(placeholder))) {
			placeholders.push(name);
		}
		result[name] = value;
	}
	if (missing.length > 0) {
		throw new SettingsError(`Missing environment variable(s): ${missing.join(", ")}`);
	}
	if (placeholders.length > 0) {
		throw new SettingsError(`Placeholder value left in: ${placeholders.join(", ")}`);
	}
	return result;
}

class SettingsError extends Error {}

/** The Django container. It sleeps when idle and starts again on the next request. */
export class BackendContainer extends Container<Env> {
	defaultPort = 8080;
	sleepAfter = "10m";

	/**
	 * Called by the Worker on every request with the settings it sees right now. A running
	 * container keeps the environment it started with, and this object can outlive a
	 * secret change, so compare a fingerprint of the settings with the one the container
	 * was started with and restart it when they differ. Only the hash is stored.
	 */
	async syncSettings(settings: Record<string, string>): Promise<void> {
		const fingerprint = await settingsFingerprint(settings);
		this.envVars = settings;
		if ((await this.ctx.storage.get<string>(FINGERPRINT_KEY)) !== fingerprint) {
			if (this.ctx.container?.running) await this.stop();
			await this.ctx.storage.put(FINGERPRINT_KEY, fingerprint);
		}
	}
}

const FINGERPRINT_KEY = "settings-fingerprint";

/** SHA-256 of the settings, so the values themselves are never stored. */
async function settingsFingerprint(settings: Record<string, string>): Promise<string> {
	const text = JSON.stringify(Object.entries(settings).sort(([a], [b]) => a.localeCompare(b)));
	const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
	return [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

export default {
	async fetch(request: Request, env: Env): Promise<Response> {
		// Tell Django the original scheme and client address (it sees only this Worker)
		const headers = new Headers(request.headers);
		headers.set("X-Forwarded-Proto", "https");
		const clientIp = request.headers.get("CF-Connecting-IP");
		if (clientIp) headers.set("X-Forwarded-For", clientIp);

		const backend = env.BACKEND.getByName("backend");
		try {
			await backend.syncSettings(containerEnv(env));
		} catch (error) {
			if (error instanceof SettingsError) {
				return new Response(error.message, { status: 500 });
			}
			throw error;
		}
		return backend.fetch(new Request(request, { headers }));
	},
} satisfies ExportedHandler<Env>;
