import pg from "pg";
import { config } from "./config.js";

export const pool = new pg.Pool({
  connectionString: config.DATABASE_URL,
  max: 10,
});

export type Row = pg.QueryResultRow;

export async function q<T extends Row = Row>(
  text: string,
  params: unknown[] = []
): Promise<T[]> {
  const res = await pool.query<T>(text, params);
  return res.rows;
}

export async function q1<T extends Row = Row>(
  text: string,
  params: unknown[] = []
): Promise<T | undefined> {
  const rows = await q<T>(text, params);
  return rows[0];
}
