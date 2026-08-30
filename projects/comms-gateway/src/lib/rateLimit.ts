import { redis } from "../redis.js";

// Compteur quotidien par (client_id, channel) via shared-redis.
// Clé : ratelimit:<client_id>:<channel>:<YYYY-MM-DD utc>
// TTL : jusqu'à la fin du jour courant (remise à zéro quotidienne).

function dayKey(date = new Date()): string {
  return date.toISOString().slice(0, 10);
}

function ttlToMidnightUtc(now = new Date()): number {
  const end = new Date(now);
  end.setUTCHours(24, 0, 0, 0);
  return Math.max(1, Math.round((end.getTime() - now.getTime()) / 1000));
}

export async function checkRateLimit(
  clientId: string,
  channel: string,
  limitPerDay: number
): Promise<{ allowed: boolean; used: number }> {
  if (limitPerDay <= 0) return { allowed: true, used: 0 };
  const key = `ratelimit:${clientId}:${channel}:${dayKey()}`;
  const used = await redis.incr(key);
  if (used === 1) {
    await redis.expire(key, ttlToMidnightUtc());
  }
  return { allowed: used <= limitPerDay, used };
}
