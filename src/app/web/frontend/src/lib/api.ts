import type { ParsedPlaylist, PlaylistSummary } from './types';

const API_BASE = '/api';

async function fetchJson<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

// Playlists API
export async function listPlaylists(): Promise<PlaylistSummary[]> {
  return fetchJson<PlaylistSummary[]>('/playlists');
}

export async function getPlaylist(slug: string): Promise<ParsedPlaylist> {
  return fetchJson<ParsedPlaylist>(`/playlists/${slug}`);
}

export async function updatePlaylist(
  slug: string,
  data: { blocks: ParsedPlaylist['blocks']; source_name?: string | null }
): Promise<ParsedPlaylist> {
  return fetchJson<ParsedPlaylist>(`/playlists/${slug}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function deletePlaylist(slug: string, alsoSpotify = false): Promise<void> {
  await fetchJson(`/playlists/${slug}?also_spotify=${alsoSpotify}`, {
    method: 'DELETE',
  });
}

// Health check
export async function healthCheck(): Promise<{ status: string }> {
  return fetchJson<{ status: string }>('/health');
}
