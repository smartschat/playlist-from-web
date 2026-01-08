import type { ParsedPlaylist, PlaylistSummary, SpotifyArtifact, SpotifySearchResult } from './types';

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

// Spotify API
export async function getSpotifyArtifact(slug: string): Promise<SpotifyArtifact | null> {
  try {
    return await fetchJson<SpotifyArtifact>(`/spotify/${slug}`);
  } catch {
    return null;
  }
}

export async function searchSpotify(artist: string, title: string): Promise<SpotifySearchResult[]> {
  return fetchJson<SpotifySearchResult[]>('/spotify/search', {
    method: 'POST',
    body: JSON.stringify({ artist, title }),
  });
}

export async function remapPlaylist(slug: string): Promise<SpotifyArtifact> {
  return fetchJson<SpotifyArtifact>(`/spotify/${slug}/remap`, {
    method: 'POST',
  });
}

export async function assignTrackUri(
  slug: string,
  blockIdx: number,
  trackIdx: number,
  uri: string,
  url?: string
): Promise<SpotifyArtifact> {
  return fetchJson<SpotifyArtifact>(`/spotify/${slug}/tracks/${blockIdx}/${trackIdx}/assign`, {
    method: 'POST',
    body: JSON.stringify({ uri, url }),
  });
}

export async function updateSpotifyPlaylist(
  playlistId: string,
  name?: string,
  description?: string,
  slug?: string
): Promise<void> {
  const params = slug ? `?slug=${slug}` : '';
  await fetchJson(`/spotify/playlists/${playlistId}${params}`, {
    method: 'PUT',
    body: JSON.stringify({ name, description }),
  });
}

export async function syncSpotifyPlaylist(playlistId: string, slug: string): Promise<{ tracks_synced: number }> {
  return fetchJson<{ tracks_synced: number }>(`/spotify/playlists/${playlistId}/sync?slug=${slug}`, {
    method: 'POST',
  });
}

export async function deleteSpotifyPlaylist(playlistId: string, slug?: string): Promise<void> {
  const params = slug ? `?slug=${slug}` : '';
  await fetchJson(`/spotify/playlists/${playlistId}${params}`, {
    method: 'DELETE',
  });
}
