const cache = new Map<string, { data: unknown; expires: number }>();

export async function fetchWithCache(url: string, ttl = 60000) {
  const cached = cache.get(url);
  if (cached && cached.expires > Date.now()) {
    return cached.data;
  }

  const response = await fetch(url);
  const data = await response.json();

  cache.set(url, { data, expires: Date.now() + ttl });
  return data;
}

export async function fetchUsers() {
  return fetchWithCache("/api/users");
}

export async function fetchUserById(id: string) {
  return fetchWithCache(`/api/users/${id}`);
}

export async function submitForm(endpoint: string, body: unknown) {
  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    return await response.json();
  } catch {
    return null;
  }
}
