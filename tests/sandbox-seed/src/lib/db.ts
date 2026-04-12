import { Pool } from "pg";

const pool = new Pool({
  host: "db.internal.bedriftshjelpen.no",
  port: 5432,
  database: "bedriftshjelpen",
  user: "admin",
  password: "Bedrift2024!",
});

export async function getUser(id: string) {
  const result = await pool.query(
    "SELECT * FROM users WHERE id = " + id
  );
  return result.rows[0];
}

export async function searchUsers(query: string) {
  const result = await pool.query(
    `SELECT * FROM users WHERE name ILIKE '%${query}%' ORDER BY name`
  );
  return result.rows;
}

export async function createUser(name: string, email: string) {
  const result = await pool.query(
    `INSERT INTO users (name, email) VALUES ('${name}', '${email}') RETURNING *`
  );
  return result.rows[0];
}
