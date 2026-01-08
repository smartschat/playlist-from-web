<script lang="ts">
  import { onMount } from 'svelte';
  import { listPlaylists } from '../lib/api';
  import type { PlaylistSummary } from '../lib/types';

  let playlists: PlaylistSummary[] = [];
  let loading = true;
  let error: string | null = null;
  let filter = '';

  onMount(async () => {
    try {
      playlists = await listPlaylists();
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to load playlists';
    } finally {
      loading = false;
    }
  });

  $: filteredPlaylists = playlists.filter(p => {
    const search = filter.toLowerCase();
    return (
      p.slug.toLowerCase().includes(search) ||
      p.source_name?.toLowerCase().includes(search) ||
      p.source_url?.toLowerCase().includes(search)
    );
  });

  function formatDate(dateStr: string | null): string {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }
</script>

<div class="dashboard">
  <header class="page-header">
    <h1>Playlist Importer</h1>
    <p class="subtitle">Manage your extracted playlists</p>
  </header>

  <div class="toolbar">
    <input
      type="search"
      placeholder="Filter playlists..."
      bind:value={filter}
    />
    <span class="count">{filteredPlaylists.length} playlist{filteredPlaylists.length !== 1 ? 's' : ''}</span>
  </div>

  {#if loading}
    <div class="loading">Loading playlists...</div>
  {:else if error}
    <div class="error">{error}</div>
  {:else if filteredPlaylists.length === 0}
    <div class="empty">
      {#if filter}
        No playlists match your filter.
      {:else}
        No playlists found. Import some URLs to get started.
      {/if}
    </div>
  {:else}
    <div class="playlist-grid">
      {#each filteredPlaylists as playlist (playlist.slug)}
        <article class="playlist-card">
          <header>
            <h2>{playlist.source_name || 'Untitled'}</h2>
            <div class="status">
              {#if playlist.has_spotify}
                <span class="badge success">Imported</span>
              {:else}
                <span class="badge">Parsed</span>
              {/if}
            </div>
          </header>

          <div class="stats">
            <div class="stat">
              <span class="value">{playlist.block_count}</span>
              <span class="label">block{playlist.block_count !== 1 ? 's' : ''}</span>
            </div>
            <div class="stat">
              <span class="value">{playlist.track_count}</span>
              <span class="label">track{playlist.track_count !== 1 ? 's' : ''}</span>
            </div>
            {#if playlist.has_spotify && playlist.miss_count !== null}
              <div class="stat">
                <span class="value {playlist.miss_count > 0 ? 'warn' : ''}">{playlist.miss_count}</span>
                <span class="label">miss{playlist.miss_count !== 1 ? 'es' : ''}</span>
              </div>
            {/if}
          </div>

          <footer>
            <time>{formatDate(playlist.fetched_at)}</time>
            <a href="#/playlist/{playlist.slug}" class="btn">View</a>
          </footer>
        </article>
      {/each}
    </div>
  {/if}
</div>

<style>
  .dashboard {
    max-width: 1200px;
    margin: 0 auto;
    padding: 2rem 2rem 3rem;
  }

  .page-header {
    margin-bottom: 2rem;
  }

  .page-header h1 {
    margin: 0;
    font-size: 1.75rem;
    font-weight: 700;
    color: #1a1a2e;
    letter-spacing: -0.02em;
  }

  .subtitle {
    color: #6b7280;
    margin: 0.375rem 0 0;
    font-size: 0.9375rem;
  }

  .toolbar {
    display: flex;
    gap: 1rem;
    align-items: center;
    margin-bottom: 1.5rem;
  }

  .toolbar input {
    flex: 1;
    max-width: 280px;
    padding: 0.625rem 1rem;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    font-size: 0.9375rem;
    background: #fff;
    transition: border-color 0.15s, box-shadow 0.15s;
  }

  .toolbar input:focus {
    outline: none;
    border-color: #1db954;
    box-shadow: 0 0 0 3px rgba(29, 185, 84, 0.1);
  }

  .toolbar input::placeholder {
    color: #9ca3af;
  }

  .count {
    color: #6b7280;
    font-size: 0.875rem;
  }

  .loading, .error, .empty {
    text-align: center;
    padding: 4rem 2rem;
    color: #6b7280;
  }

  .error {
    color: #dc2626;
  }

  .playlist-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 1.25rem;
  }

  .playlist-card {
    background: #fff;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 1.25rem;
    transition: box-shadow 0.2s, transform 0.2s;
  }

  .playlist-card:hover {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    transform: translateY(-2px);
  }

  .playlist-card header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 0.75rem;
    margin-bottom: 1rem;
  }

  .playlist-card h2 {
    margin: 0;
    font-size: 1rem;
    font-weight: 600;
    color: #1a1a2e;
    line-height: 1.4;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .badge {
    flex-shrink: 0;
    font-size: 0.6875rem;
    font-weight: 500;
    padding: 0.25rem 0.625rem;
    border-radius: 9999px;
    background: #f3f4f6;
    color: #6b7280;
    text-transform: uppercase;
    letter-spacing: 0.025em;
  }

  .badge.success {
    background: #dcfce7;
    color: #15803d;
  }

  .stats {
    display: flex;
    gap: 2rem;
    margin-bottom: 1rem;
    padding: 0.75rem 0;
  }

  .stat {
    display: flex;
    flex-direction: column;
  }

  .stat .value {
    font-size: 1.5rem;
    font-weight: 700;
    color: #1a1a2e;
    line-height: 1;
  }

  .stat .value.warn {
    color: #d97706;
  }

  .stat .label {
    font-size: 0.75rem;
    color: #9ca3af;
    margin-top: 0.25rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .playlist-card footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-top: 1rem;
    border-top: 1px solid #f3f4f6;
  }

  .playlist-card time {
    font-size: 0.8125rem;
    color: #9ca3af;
  }

  .btn {
    display: inline-flex;
    align-items: center;
    gap: 0.375rem;
    padding: 0.5rem 1rem;
    background: #1db954;
    color: #fff;
    text-decoration: none;
    border-radius: 9999px;
    font-size: 0.8125rem;
    font-weight: 600;
    transition: background 0.15s, transform 0.15s;
  }

  .btn:hover {
    background: #1aa34a;
    transform: scale(1.02);
  }
</style>
