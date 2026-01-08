// Types mirroring Python models

export interface Track {
  artist: string;
  title: string;
  album: string | null;
  source_line: string | null;
  spotify_uri?: string;
  spotify_url?: string;
}

export interface TrackBlock {
  title: string;
  context: string | null;
  tracks: Track[];
}

export interface ParsedPlaylist {
  source_url: string;
  source_name: string | null;
  fetched_at: string;
  blocks: TrackBlock[];
}

export interface PlaylistSummary {
  slug: string;
  source_url: string | null;
  source_name: string | null;
  fetched_at: string | null;
  block_count: number;
  track_count: number;
  has_spotify: boolean;
  miss_count: number | null;
  playlist_count: number | null;
}

export interface SpotifyPlaylist {
  id: string;
  name: string;
  url: string;
  tracks: string[];
  tracks_added: number;
}

export interface SpotifyArtifact {
  source_url: string;
  parsed_artifact: string;
  blocks: TrackBlock[];
  playlists: SpotifyPlaylist[];
  master_playlist: SpotifyPlaylist | null;
  misses: { block: string; artist: string; title: string }[];
  failed_tracks: string[];
  generated_at: string;
}

export interface CrawlSummary {
  slug: string;
  index_url: string;
  crawled_at: string;
  link_count: number;
  success_count: number;
  skipped_count: number;
  failed_count: number;
}
