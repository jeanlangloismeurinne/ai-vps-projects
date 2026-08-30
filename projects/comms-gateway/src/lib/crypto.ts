import crypto from "node:crypto";
import { config } from "../config.js";

// --- Hash des tokens clients (jamais stockés en clair) ---
export function hashToken(token: string): string {
  return crypto.createHash("sha256").update(token).digest("hex");
}

export function generateToken(): string {
  return crypto.randomBytes(24).toString("hex"); // 48 hex chars, unique et non devinable
}

// --- Chiffrement des credentials providers (AES-256-GCM) avec MASTER_KEY ---
// Permet de stocker plusieurs comptes (ex. plusieurs clés Resend) dans
// `provider_accounts.creds` sans exposer les secrets en clair.
function masterKeyBuf(): Buffer {
  if (!config.MASTER_KEY) {
    throw new Error("MASTER_KEY manquante — chiffrement des creds impossible");
  }
  return Buffer.from(config.MASTER_KEY, "base64");
}

export function encryptCreds(creds: Record<string, unknown>): string {
  const iv = crypto.randomBytes(12);
  const cipher = crypto.createCipheriv("aes-256-gcm", masterKeyBuf(), iv);
  const pt = Buffer.from(JSON.stringify(creds), "utf8");
  const ct = Buffer.concat([cipher.update(pt), cipher.final()]);
  const tag = cipher.getAuthTag();
  return [iv, tag, ct].map((b) => b.toString("base64")).join(".");
}

export function decryptCreds(payload: string): Record<string, unknown> {
  const [ivB64, tagB64, ctB64] = payload.split(".");
  const decipher = crypto.createDecipheriv(
    "aes-256-gcm",
    masterKeyBuf(),
    Buffer.from(ivB64, "base64")
  );
  decipher.setAuthTag(Buffer.from(tagB64, "base64"));
  const pt = Buffer.concat([
    decipher.update(Buffer.from(ctB64, "base64")),
    decipher.final(),
  ]);
  return JSON.parse(pt.toString("utf8"));
}

// --- Vérification signature Svix (webhook Resend entrant) ---
// Format: header "svix-id", "svix-timestamp", "svix-signature" (ed25519).
export function verifySvix(
  payload: Buffer,
  headers: Record<string, string | string[] | undefined>,
  secret: string
): boolean {
  const h = (n: string) => headers[n] ?? headers[n.toLowerCase()];
  const id = String(h("svix-id") ?? "");
  const ts = String(h("svix-timestamp") ?? "");
  const sigHeader = String(h("svix-signature") ?? "");
  if (!id || !ts || !sigHeader) return false;

  // L'âge du timestamp doit rester raisonnable (anti-rejeu)
  if (Math.abs(Date.now() / 1000 - Number(ts)) > 300) return false;

  const toSign = Buffer.concat([Buffer.from(id + "." + ts + "."), payload]);

  // Le secret Svix contient le secret et son ID : "whsec_<id>.<secret>"
  let secretMaterial = secret;
  let expectedParts: string[] = [];
  if (secret.startsWith("whsec_") && secret.includes(".")) {
    secretMaterial = secret.split(".").slice(1).join(".");
  } else {
    // Format whsec_<base64-unique>
    secretMaterial = secret.replace(/^whsec_/, "");
  }

  const keyBase64 = Buffer.from(secretMaterial, "base64").toString("utf8");
  let publicKey: Buffer;
  try {
    publicKey = Buffer.from(
      crypto.createPublicKey({ key: keyBase64, format: "pem" }).export({
        format: "der",
        type: "spki",
      })
    );
  } catch {
    return false;
  }

  // ed25519 : lsig.<b64sig>.<b64keyid>
  for (const part of sigHeader.split(" ")) {
    if (!part.startsWith("v1,")) continue;
    const sigB64 = part.replace("v1,", "");
    try {
      const verifier = crypto.createVerify("ed25519");
      verifier.update(toSign);
      const ok = verifier.verify(
        { key: publicKey, format: "der", type: "spki" },
        Buffer.from(sigB64, "base64")
      );
      if (ok) return true;
    } catch {
      /* try next */
    }
  }
  return false;
}

// --- Vérification signature Slack (HTTP Events API) ---
export function verifySlackSignature(
  body: string,
  headers: Record<string, string | string[] | undefined>,
  signingSecret: string
): boolean {
  const h = (n: string) => headers[n] ?? headers[n.toLowerCase()];
  const ts = String(h("x-slack-request-timestamp") ?? "");
  const sig = String(h("x-slack-signature") ?? "");
  if (!ts || !sig) return false;
  // Tolérance anti-rejeu (5 min)
  if (Math.abs(Date.now() / 1000 - Number(ts)) > 300) return false;
  const base = `v0:${ts}:${body}`;
  const expected = "v0=" + crypto.createHmac("sha256", signingSecret).update(base).digest("hex");
  return crypto.timingSafeEqual(Buffer.from(expected), Buffer.from(sig));
}
