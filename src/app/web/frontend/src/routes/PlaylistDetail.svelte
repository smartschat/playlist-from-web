<script lang="ts">
  import { onMount } from 'svelte';
  import { getPlaylist, updatePlaylist, getSpotifyArtifact } from '../lib/api';
  import type { ParsedPlaylist, TrackBlock, SpotifyArtifact } from '../lib/types';
  import BlockCard from '../components/BlockCard.svelte';
  import SpotifyPanel from '../components/SpotifyPanel.svelte';

  export let slug: string;

  let playlist: ParsedPlaylist | null = null;
  let spotifyArtifact: SpotifyArtifact | null = null;
  let loading = true;
  let error: string | null = null;
  let editMode = false;
  let saving = false;
  let hasChanges = false;

  // Keep a copy of the original for comparison
  let originalPlaylist: ParsedPlaylist | null = null;

  onMount(async () => {
    try {
      const [playlistData, spotifyData] = await Promise.all([
        getPlaylist(slug),
        getSpotifyArtifact(slug),
      ]);
      playlist = playlistData;
      spotifyArtifact = spotifyData;
      originalPlaylist = JSON.parse(JSON.stringify(playlist));
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to load playlist';
    } finally {
      loading = false;
    }
  });

  function getTotalTracks(p: ParsedPlaylist): number {
    return p.blocks.reduce((sum, block) => sum + block.tracks.length, 0);
  }

  function checkChanges() {
    if (!playlist || !originalPlaylist) return;
    hasChanges = JSON.stringify(playlist) !== JSON.stringify(originalPlaylist);
  }

  function toggleEditMode() {
    if (editMode && hasChanges) {
      if (!confirm('You have unsaved changes. Discard them?')) {
        return;
      }
      // Revert changes
      playlist = JSON.parse(JSON.stringify(originalPlaylist));
      hasChanges = false;
    }
    editMode = !editMode;
  }

  function handleBlockUpdate(index: number, updatedBlock: TrackBlock) {
    if (!playlist) return;
    const newBlocks = [...playlist.blocks];
    newBlocks[index] = updatedBlock;
    playlist = { ...playlist, blocks: newBlocks };
    checkChanges();
  }

  function handleBlockDelete(index: number) {
    if (!playlist) return;
    if (!confirm('Delete this block and all its tracks?')) return;
    const newBlocks = playlist.blocks.filter((_, i) => i !== index);
    playlist = { ...playlist, blocks: newBlocks };
    checkChanges();
  }

  function handleAddBlock() {
    if (!playlist) return;
    const newBlock: TrackBlock = {
      title: `Block ${playlist.blocks.length + 1}`,
      context: null,
      tracks: []
    };
    playlist = { ...playlist, blocks: [...playlist.blocks, newBlock] };
    checkChanges();
  }

  async function handleSave() {
    if (!playlist || saving) return;

    saving = true;
    error = null;

    try {
      const updated = await updatePlaylist(slug, {
        blocks: playlist.blocks,
        source_name: playlist.source_name
      });
      playlist = updated;
      originalPlaylist = JSON.parse(JSON.stringify(updated));
      hasChanges = false;
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to save changes';
    } finally {
      saving = false;
    }
  }

  // Handle beforeunload to warn about unsaved changes
  function handleBeforeUnload(e: BeforeUnloadEvent) {
    if (hasChanges) {
      e.preventDefault();
      e.returnValue = '';
    }
  }

  function handleSpotifyUpdate(e: CustomEvent<SpotifyArtifact>) {
    spotifyArtifact = e.detail;
  }
</script>

<svelte:window on:beforeunload={handleBeforeUnload} />

<div class="playlist-detail">
  <nav class="breadcrumb">
    <a href="#/">Dashboard</a>
    <span class="separator">/</span>
    <span class="current">{playlist?.source_name || slug}</span>
  </nav>

  {#if loading}
    <div class="loading">Loading playlist...</div>
  {:else if error && !playlist}
    <div class="error">{error}</div>
  {:else if playlist}
    <header class="page-header">
      <div class="header-left">
        <h1>{playlist.source_name || 'Untitled Playlist'}</h1>
        <p class="meta">
          {playlist.blocks.length} block{playlist.blocks.length !== 1 ? 's' : ''} &middot;
          {getTotalTracks(playlist)} track{getTotalTracks(playlist) !== 1 ? 's' : ''}
        </p>
        {#if playlist.source_url}
          <a href={playlist.source_url} target="_blank" rel="noopener" class="source-link">
            View source
          </a>
        {/if}
      </div>

      <div class="header-actions">
        {#if hasChanges}
          <span class="unsaved-badge">Unsaved changes</span>
        {/if}

        {#if editMode}
          <button class="btn btn-secondary" on:click={toggleEditMode} disabled={saving}>
            Cancel
          </button>
          <button class="btn btn-primary" on:click={handleSave} disabled={saving || !hasChanges}>
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        {:else}
          <button class="btn btn-edit" on:click={toggleEditMode}>
            Edit
          </button>
        {/if}
      </div>
    </header>

    {#if error}
      <div class="error-banner">{error}</div>
    {/if}

    <div class="blocks">
      {#each playlist.blocks as block, blockIndex (blockIndex)}
        <BlockCard
          {block}
          {blockIndex}
          {editMode}
          on:update={(e) => handleBlockUpdate(blockIndex, e.detail)}
          on:delete={() => handleBlockDelete(blockIndex)}
        />
      {/each}

      {#if editMode}
        <button class="add-block-btn" on:click={handleAddBlock}>
          + Add Block
        </button>
      {/if}
    </div>

    <section class="spotify-section">
      {#if spotifyArtifact}
        <SpotifyPanel {slug} artifact={spotifyArtifact} on:update={handleSpotifyUpdate} />
      {:else}
        <div class="no-spotify">
          <p>No Spotify data available for this playlist.</p>
          <p class="hint">Import this playlist to Spotify using the CLI to enable Spotify integration.</p>
        </div>
      {/if}
    </section>
  {/if}
</div>

<style>
  .playlist-detail {
    max-width: 1000px;
    margin: 0 auto;
    padding: 2rem;
  }

  .breadcrumb {
    margin-bottom: 1.5rem;
    font-size: 0.875rem;
  }

  .breadcrumb a {
    color: #1db954;
    text-decoration: none;
  }

  .breadcrumb a:hover {
    text-decoration: underline;
  }

  .breadcrumb .separator {
    margin: 0 0.5rem;
    color: #999;
  }

  .breadcrumb .current {
    color: #666;
  }

  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 1rem;
    margin-bottom: 2rem;
  }

  .header-left h1 {
    margin: 0 0 0.5rem;
    font-size: 1.75rem;
  }

  .meta {
    color: #666;
    margin: 0 0 0.5rem;
  }

  .source-link {
    font-size: 0.875rem;
    color: #1db954;
    text-decoration: none;
  }

  .source-link:hover {
    text-decoration: underline;
  }

  .header-actions {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    flex-shrink: 0;
  }

  .unsaved-badge {
    padding: 0.375rem 0.75rem;
    background: #fef3c7;
    color: #92400e;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 500;
  }

  .btn {
    padding: 0.625rem 1.25rem;
    border-radius: 8px;
    font-size: 0.875rem;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.15s, opacity 0.15s, transform 0.15s;
  }

  .btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .btn-edit {
    background: #f3f4f6;
    border: 1px solid #e5e7eb;
    color: #374151;
  }

  .btn-edit:hover:not(:disabled) {
    background: #e5e7eb;
  }

  .btn-secondary {
    background: #fff;
    border: 1px solid #e5e7eb;
    color: #374151;
  }

  .btn-secondary:hover:not(:disabled) {
    background: #f3f4f6;
  }

  .btn-primary {
    background: #1db954;
    border: none;
    color: #fff;
  }

  .btn-primary:hover:not(:disabled) {
    background: #1aa34a;
    transform: scale(1.02);
  }

  .loading, .error {
    text-align: center;
    padding: 3rem;
    color: #666;
  }

  .error {
    color: #dc2626;
  }

  .error-banner {
    background: #fee2e2;
    color: #dc2626;
    padding: 0.75rem 1rem;
    border-radius: 8px;
    margin-bottom: 1rem;
    font-size: 0.875rem;
  }

  .blocks {
    margin-top: 1rem;
  }

  .add-block-btn {
    width: 100%;
    padding: 1rem;
    background: none;
    border: 2px dashed #ccc;
    border-radius: 8px;
    color: #666;
    font-size: 0.875rem;
    cursor: pointer;
    transition: border-color 0.15s, color 0.15s, background 0.15s;
  }

  .add-block-btn:hover {
    border-color: #1db954;
    color: #1db954;
    background: #f0fdf4;
  }

  .spotify-section {
    margin-top: 3rem;
  }

  .no-spotify {
    text-align: center;
    padding: 2rem;
    background: #f9fafb;
    border: 1px dashed #e5e7eb;
    border-radius: 12px;
    color: #666;
  }

  .no-spotify p {
    margin: 0.5rem 0;
  }

  .no-spotify .hint {
    font-size: 0.875rem;
    color: #999;
  }
</style>
