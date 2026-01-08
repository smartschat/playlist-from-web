<script lang="ts">
  import type { SpotifyPlaylist } from '../lib/types';
  import { createEventDispatcher } from 'svelte';

  export let playlist: SpotifyPlaylist;
  export let slug: string;
  export let isMaster: boolean = false;

  const dispatch = createEventDispatcher<{
    sync: SpotifyPlaylist;
    delete: SpotifyPlaylist;
    rename: { playlist: SpotifyPlaylist; newName: string };
  }>();

  let editing = false;
  let editName = playlist.name;
  let syncing = false;
  let deleting = false;

  function startEdit() {
    editing = true;
    editName = playlist.name;
  }

  function cancelEdit() {
    editing = false;
    editName = playlist.name;
  }

  function saveEdit() {
    if (editName.trim() && editName !== playlist.name) {
      dispatch('rename', { playlist, newName: editName.trim() });
    }
    editing = false;
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter') {
      e.preventDefault();
      saveEdit();
    } else if (e.key === 'Escape') {
      cancelEdit();
    }
  }

  function handleSync() {
    syncing = true;
    dispatch('sync', playlist);
    // Parent will handle the actual sync and reset syncing state
  }

  function handleDelete() {
    if (confirm(`Delete playlist "${playlist.name}" from Spotify?`)) {
      deleting = true;
      dispatch('delete', playlist);
    }
  }

  // Reset loading states when playlist changes
  $: if (playlist) {
    syncing = false;
    deleting = false;
  }
</script>

<div class="playlist-card" class:master={isMaster}>
  <div class="card-header">
    {#if isMaster}
      <span class="master-badge">Master</span>
    {/if}
    {#if editing}
      <input
        type="text"
        bind:value={editName}
        on:keydown={handleKeydown}
        on:blur={saveEdit}
        class="name-input"
        autofocus
      />
    {:else}
      <h4 class="name" on:dblclick={startEdit}>
        <a href={playlist.url} target="_blank" rel="noopener noreferrer">
          {playlist.name}
        </a>
      </h4>
    {/if}
  </div>

  <div class="card-body">
    <div class="stats">
      <span class="stat">
        <span class="stat-value">{playlist.tracks_added}</span>
        <span class="stat-label">tracks</span>
      </span>
    </div>
  </div>

  <div class="card-actions">
    <button class="btn btn-edit" on:click={startEdit} title="Rename playlist">
      Rename
    </button>
    <button
      class="btn btn-sync"
      on:click={handleSync}
      disabled={syncing}
      title="Sync tracks to Spotify"
    >
      {syncing ? 'Syncing...' : 'Sync'}
    </button>
    <button
      class="btn btn-delete"
      on:click={handleDelete}
      disabled={deleting}
      title="Delete from Spotify"
    >
      {deleting ? 'Deleting...' : 'Delete'}
    </button>
  </div>
</div>

<style>
  .playlist-card {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 1rem;
    transition: box-shadow 0.15s;
  }

  .playlist-card:hover {
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  }

  .playlist-card.master {
    border-color: #1db954;
    background: linear-gradient(to bottom, #f0fdf4, white);
  }

  .card-header {
    margin-bottom: 0.75rem;
  }

  .master-badge {
    display: inline-block;
    background: #1db954;
    color: white;
    font-size: 0.625rem;
    font-weight: 600;
    text-transform: uppercase;
    padding: 0.125rem 0.5rem;
    border-radius: 4px;
    margin-bottom: 0.5rem;
  }

  .name {
    margin: 0;
    font-size: 1rem;
    font-weight: 600;
  }

  .name a {
    color: #1a1a2e;
    text-decoration: none;
  }

  .name a:hover {
    color: #1db954;
    text-decoration: underline;
  }

  .name-input {
    width: 100%;
    padding: 0.375rem 0.5rem;
    border: 2px solid #1db954;
    border-radius: 4px;
    font-size: 1rem;
    font-weight: 600;
    font-family: inherit;
  }

  .name-input:focus {
    outline: none;
    box-shadow: 0 0 0 3px rgba(29, 185, 84, 0.2);
  }

  .card-body {
    margin-bottom: 0.75rem;
  }

  .stats {
    display: flex;
    gap: 1rem;
  }

  .stat {
    display: flex;
    align-items: baseline;
    gap: 0.25rem;
  }

  .stat-value {
    font-size: 1.25rem;
    font-weight: 600;
    color: #1db954;
  }

  .stat-label {
    font-size: 0.75rem;
    color: #666;
  }

  .card-actions {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
  }

  .btn {
    padding: 0.375rem 0.75rem;
    border: none;
    border-radius: 4px;
    font-size: 0.75rem;
    cursor: pointer;
    transition: background 0.15s;
  }

  .btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .btn-edit {
    background: #e5e7eb;
    color: #374151;
  }

  .btn-edit:hover:not(:disabled) {
    background: #d1d5db;
  }

  .btn-sync {
    background: #1db954;
    color: white;
  }

  .btn-sync:hover:not(:disabled) {
    background: #1aa34a;
  }

  .btn-delete {
    background: #fee2e2;
    color: #dc2626;
  }

  .btn-delete:hover:not(:disabled) {
    background: #fecaca;
  }
</style>
