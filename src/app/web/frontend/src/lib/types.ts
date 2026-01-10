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
  llm_usage?: LLMUsage;
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
  llm_cost_usd: number | null;
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
  llm_cost_usd: number | null;
}

export interface SpotifySearchResult {
  uri: string;
  name: string;
  artists: string[];
  album: string;
  url: string;
}

export interface Miss {
  block: string;
  artist: string;
  title: string;
}

// Import types
export interface ImportPreviewResponse {
  slug: string;
  source_url: string;
  source_name: string | null;
  block_count: number;
  track_count: number;
  blocks: TrackBlock[];
  llm_cost_usd: number | null;
}

export interface ImportExecuteResponse {
  slug: string;
  source_url: string;
  playlist_count: number;
  miss_count: number;
  has_master: boolean;
  llm_cost_usd: number | null;
}

// Crawl types
export interface CrawlProcessedEntry {
  url: string;
  description?: string;
  status: 'success' | 'skipped' | 'failed';
  mode?: string;
  artifact?: string;
  error?: string;
  llm_cost_usd?: number;
}

export interface LLMUsage {
  prompt_tokens: number;
  completion_tokens: number;
  model: string;
  cost_usd: number;
}

export interface CrawlDetail {
  index_url: string;
  discovered_links: { url: string; description: string }[];
  processed: CrawlProcessedEntry[];
  crawled_at: string;
  llm_usage?: LLMUsage;
}
