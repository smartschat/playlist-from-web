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
  <header>
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
    padding: 2rem;
  }

  header h1 {
    margin: 0;
    font-size: 2rem;
  }

  .subtitle {
    color: #666;
    margin: 0.5rem 0 2rem;
  }

  .toolbar {
    display: flex;
    gap: 1rem;
    align-items: center;
    margin-bottom: 1.5rem;
  }

  .toolbar input {
    flex: 1;
    max-width: 300px;
    padding: 0.5rem 1rem;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 1rem;
  }

  .count {
    color: #666;
    font-size: 0.875rem;
  }

  .loading, .error, .empty {
    text-align: center;
    padding: 3rem;
    color: #666;
  }

  .error {
    color: #c00;
  }

  .playlist-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 1rem;
  }

  .playlist-card {
    background: #fff;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 1rem;
    transition: box-shadow 0.2s;
  }

  .playlist-card:hover {
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }

  .playlist-card header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 1rem;
  }

  .playlist-card h2 {
    margin: 0;
    font-size: 1rem;
    font-weight: 600;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 200px;
  }

  .badge {
    font-size: 0.75rem;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    background: #e0e0e0;
    color: #333;
  }

  .badge.success {
    background: #d4edda;
    color: #155724;
  }

  .stats {
    display: flex;
    gap: 1.5rem;
    margin-bottom: 1rem;
  }

  .stat {
    display: flex;
    flex-direction: column;
    align-items: center;
  }

  .stat .value {
    font-size: 1.25rem;
    font-weight: 600;
  }

  .stat .value.warn {
    color: #856404;
  }

  .stat .label {
    font-size: 0.75rem;
    color: #666;
  }

  .playlist-card footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-top: 1rem;
    border-top: 1px solid #eee;
  }

  .playlist-card time {
    font-size: 0.75rem;
    color: #888;
  }

  .btn {
    display: inline-block;
    padding: 0.375rem 0.75rem;
    background: #007bff;
    color: #fff;
    text-decoration: none;
    border-radius: 4px;
    font-size: 0.875rem;
    transition: background 0.2s;
  }

  .btn:hover {
    background: #0056b3;
  }
</style>
