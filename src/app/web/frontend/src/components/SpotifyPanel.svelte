<script lang="ts">
  import type { SpotifyArtifact, Miss, SpotifySearchResult, SpotifyPlaylist } from '../lib/types';
  import {
    remapPlaylist,
    assignTrackUri,
    updateSpotifyPlaylist,
    syncSpotifyPlaylist,
    deleteSpotifyPlaylist,
  } from '../lib/api';
  import SpotifyPlaylistCard from './SpotifyPlaylistCard.svelte';
  import MissRow from './MissRow.svelte';
  import SpotifySearchModal from './SpotifySearchModal.svelte';
  import { createEventDispatcher } from 'svelte';

  export let slug: string;
  export let artifact: SpotifyArtifact;

  const dispatch = createEventDispatcher<{
    update: SpotifyArtifact;
  }>();

  let activeTab: 'playlists' | 'misses' = 'playlists';
  let remapping = false;
  let error: string | null = null;

  // Modal state
  let searchModalOpen = false;
  let selectedMiss: Miss | null = null;
  let selectedMissIndex: number = -1;

  $: playlistCount = artifact.playlists.length + (artifact.master_playlist ? 1 : 0);
  $: missCount = artifact.misses.length;

  async function handleRemap() {
    remapping = true;
    error = null;

    try {
      const updated = await remapPlaylist(slug);
      dispatch('update', updated);
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to remap playlist';
    } finally {
      remapping = false;
    }
  }

  function handleSearchMiss(e: CustomEvent<Miss>) {
    const miss = e.detail;
    // Find the index of this miss
    selectedMissIndex = artifact.misses.findIndex(
      (m) => m.artist === miss.artist && m.title === miss.title && m.block === miss.block
    );
    selectedMiss = miss;
    searchModalOpen = true;
  }

  function handleIgnoreMiss(e: CustomEvent<Miss>) {
    const miss = e.detail;
    // Remove from local artifact (we don't have a backend endpoint for this yet)
    const updated = {
      ...artifact,
      misses: artifact.misses.filter(
        (m) => !(m.artist === miss.artist && m.title === miss.title && m.block === miss.block)
      ),
    };
    dispatch('update', updated);
  }

  async function handleSelectTrack(e: CustomEvent<SpotifySearchResult>) {
    const result = e.detail;
    if (selectedMiss === null) return;

    // Find block and track indices
    const blockIdx = artifact.blocks.findIndex((b) => b.title === selectedMiss!.block);
    if (blockIdx === -1) {
      error = 'Could not find block for miss';
      return;
    }

    const trackIdx = artifact.blocks[blockIdx].tracks.findIndex(
      (t) => t.artist === selectedMiss!.artist && t.title === selectedMiss!.title
    );
    if (trackIdx === -1) {
      error = 'Could not find track in block';
      return;
    }

    try {
      const updated = await assignTrackUri(slug, blockIdx, trackIdx, result.uri, result.url);
      dispatch('update', updated);
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to assign track';
    }

    searchModalOpen = false;
    selectedMiss = null;
  }

  function handleCloseModal() {
    searchModalOpen = false;
    selectedMiss = null;
  }

  async function handleRenamePlaylist(
    e: CustomEvent<{ playlist: SpotifyPlaylist; newName: string }>
  ) {
    const { playlist, newName } = e.detail;
    try {
      await updateSpotifyPlaylist(playlist.id, newName, undefined, slug);
      // Update local artifact
      const updated = { ...artifact };
      const p = updated.playlists.find((p) => p.id === playlist.id);
      if (p) p.name = newName;
      if (updated.master_playlist?.id === playlist.id) {
        updated.master_playlist.name = newName;
      }
      dispatch('update', updated);
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to rename playlist';
    }
  }

  async function handleSyncPlaylist(e: CustomEvent<SpotifyPlaylist>) {
    const playlist = e.detail;
    try {
      const result = await syncSpotifyPlaylist(playlist.id, slug);
      // Update local artifact
      const updated = { ...artifact };
      const p = updated.playlists.find((p) => p.id === playlist.id);
      if (p) p.tracks_added = result.tracks_synced;
      if (updated.master_playlist?.id === playlist.id) {
        updated.master_playlist.tracks_added = result.tracks_synced;
      }
      dispatch('update', updated);
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to sync playlist';
    }
  }

  async function handleDeletePlaylist(e: CustomEvent<SpotifyPlaylist>) {
    const playlist = e.detail;
    try {
      await deleteSpotifyPlaylist(playlist.id, slug);
      // Update local artifact
      const updated = {
        ...artifact,
        playlists: artifact.playlists.filter((p) => p.id !== playlist.id),
        master_playlist:
          artifact.master_playlist?.id === playlist.id ? null : artifact.master_playlist,
      };
      dispatch('update', updated);
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to delete playlist';
    }
  }
</script>

<div class="spotify-panel">
  <div class="panel-header">
    <h3>Spotify Integration</h3>
    <button class="btn-remap" on:click={handleRemap} disabled={remapping}>
      {remapping ? 'Re-mapping...' : 'Re-map All Tracks'}
    </button>
  </div>

  {#if error}
    <div class="error-banner">
      {error}
      <button class="dismiss" on:click={() => (error = null)}>&times;</button>
    </div>
  {/if}

  <div class="tabs">
    <button
      class="tab"
      class:active={activeTab === 'playlists'}
      on:click={() => (activeTab = 'playlists')}
    >
      Playlists
      <span class="badge">{playlistCount}</span>
    </button>
    <button
      class="tab"
      class:active={activeTab === 'misses'}
      on:click={() => (activeTab = 'misses')}
    >
      Misses
      <span class="badge" class:warning={missCount > 0}>{missCount}</span>
    </button>
  </div>

  <div class="tab-content">
    {#if activeTab === 'playlists'}
      {#if playlistCount === 0}
        <div class="empty">No Spotify playlists created yet.</div>
      {:else}
        <div class="playlist-grid">
          {#if artifact.master_playlist}
            <SpotifyPlaylistCard
              playlist={artifact.master_playlist}
              {slug}
              isMaster={true}
              on:rename={handleRenamePlaylist}
              on:sync={handleSyncPlaylist}
              on:delete={handleDeletePlaylist}
            />
          {/if}
          {#each artifact.playlists as playlist}
            <SpotifyPlaylistCard
              {playlist}
              {slug}
              on:rename={handleRenamePlaylist}
              on:sync={handleSyncPlaylist}
              on:delete={handleDeletePlaylist}
            />
          {/each}
        </div>
      {/if}
    {:else if activeTab === 'misses'}
      {#if missCount === 0}
        <div class="empty success">All tracks matched on Spotify!</div>
      {:else}
        <table class="miss-table">
          <thead>
            <tr>
              <th class="num">#</th>
              <th class="block">Block</th>
              <th class="artist">Artist</th>
              <th class="title">Title</th>
              <th class="actions">Actions</th>
            </tr>
          </thead>
          <tbody>
            {#each artifact.misses as miss, idx}
              <MissRow {miss} index={idx} on:search={handleSearchMiss} on:ignore={handleIgnoreMiss} />
            {/each}
          </tbody>
        </table>
      {/if}
    {/if}
  </div>
</div>

{#if searchModalOpen && selectedMiss}
  <SpotifySearchModal
    miss={selectedMiss}
    on:select={handleSelectTrack}
    on:close={handleCloseModal}
  />
{/if}

<style>
  .spotify-panel {
    background: #f9fafb;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    overflow: hidden;
  }

  .panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem 1.5rem;
    background: white;
    border-bottom: 1px solid #e5e7eb;
  }

  .panel-header h3 {
    margin: 0;
    font-size: 1.125rem;
    color: #1a1a2e;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .panel-header h3::before {
    content: '';
    display: inline-block;
    width: 20px;
    height: 20px;
    background: #1db954;
    border-radius: 50%;
  }

  .btn-remap {
    background: #1db954;
    color: white;
    border: none;
    padding: 0.5rem 1rem;
    border-radius: 6px;
    font-size: 0.875rem;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.15s;
  }

  .btn-remap:hover:not(:disabled) {
    background: #1aa34a;
  }

  .btn-remap:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .error-banner {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.75rem 1.5rem;
    background: #fee2e2;
    color: #dc2626;
    font-size: 0.875rem;
  }

  .error-banner .dismiss {
    background: none;
    border: none;
    font-size: 1.25rem;
    color: inherit;
    cursor: pointer;
    padding: 0;
    line-height: 1;
  }

  .tabs {
    display: flex;
    background: white;
    border-bottom: 1px solid #e5e7eb;
    padding: 0 1rem;
  }

  .tab {
    background: none;
    border: none;
    padding: 1rem 1.5rem;
    font-size: 0.875rem;
    font-weight: 500;
    color: #666;
    cursor: pointer;
    border-bottom: 2px solid transparent;
    transition: color 0.15s, border-color 0.15s;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .tab:hover {
    color: #1a1a2e;
  }

  .tab.active {
    color: #1db954;
    border-bottom-color: #1db954;
  }

  .badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 1.25rem;
    height: 1.25rem;
    padding: 0 0.375rem;
    background: #e5e7eb;
    border-radius: 10px;
    font-size: 0.75rem;
    font-weight: 600;
  }

  .tab.active .badge {
    background: #dcfce7;
    color: #15803d;
  }

  .badge.warning {
    background: #fef3c7;
    color: #d97706;
  }

  .tab-content {
    padding: 1.5rem;
    min-height: 200px;
  }

  .empty {
    text-align: center;
    color: #666;
    padding: 2rem;
  }

  .empty.success {
    color: #15803d;
    background: #dcfce7;
    border-radius: 8px;
  }

  .playlist-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 1rem;
  }

  .miss-table {
    width: 100%;
    border-collapse: collapse;
    background: white;
    border-radius: 8px;
    overflow: hidden;
  }

  .miss-table th {
    text-align: left;
    padding: 0.75rem 1rem;
    background: #f3f4f6;
    font-size: 0.75rem;
    font-weight: 600;
    color: #666;
    text-transform: uppercase;
    border-bottom: 1px solid #e5e7eb;
  }

  .miss-table th.num {
    width: 3rem;
    text-align: center;
  }

  .miss-table th.block {
    width: 150px;
  }

  .miss-table th.actions {
    width: 140px;
    text-align: right;
  }
</style>
