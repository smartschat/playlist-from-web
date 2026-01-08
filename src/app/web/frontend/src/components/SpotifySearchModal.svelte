<script lang="ts">
  import type { Miss, SpotifySearchResult } from '../lib/types';
  import { searchSpotify } from '../lib/api';
  import { createEventDispatcher, onMount } from 'svelte';

  export let miss: Miss;

  const dispatch = createEventDispatcher<{
    select: SpotifySearchResult;
    close: void;
  }>();

  let artist = miss.artist;
  let title = miss.title;
  let results: SpotifySearchResult[] = [];
  let searching = false;
  let error: string | null = null;
  let hasSearched = false;

  onMount(() => {
    // Auto-search on open
    handleSearch();
  });

  async function handleSearch() {
    if (!artist.trim() && !title.trim()) return;

    searching = true;
    error = null;
    hasSearched = true;

    try {
      results = await searchSpotify(artist.trim(), title.trim());
    } catch (e) {
      error = e instanceof Error ? e.message : 'Search failed';
      results = [];
    } finally {
      searching = false;
    }
  }

  function handleSelect(result: SpotifySearchResult) {
    dispatch('select', result);
  }

  function handleClose() {
    dispatch('close');
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') {
      handleClose();
    }
  }

  function handleBackdropClick(e: MouseEvent) {
    if (e.target === e.currentTarget) {
      handleClose();
    }
  }
</script>

<svelte:window on:keydown={handleKeydown} />

<div class="modal-backdrop" on:click={handleBackdropClick} role="dialog" aria-modal="true">
  <div class="modal">
    <div class="modal-header">
      <h3>Search Spotify</h3>
      <button class="close-btn" on:click={handleClose}>&times;</button>
    </div>

    <div class="modal-body">
      <div class="search-form">
        <div class="form-row">
          <label for="artist">Artist</label>
          <input
            id="artist"
            type="text"
            bind:value={artist}
            placeholder="Artist name"
          />
        </div>
        <div class="form-row">
          <label for="title">Title</label>
          <input
            id="title"
            type="text"
            bind:value={title}
            placeholder="Track title"
          />
        </div>
        <button
          class="btn-search"
          on:click={handleSearch}
          disabled={searching || (!artist.trim() && !title.trim())}
        >
          {searching ? 'Searching...' : 'Search'}
        </button>
      </div>

      {#if error}
        <div class="error">{error}</div>
      {/if}

      {#if searching}
        <div class="loading">Searching Spotify...</div>
      {:else if hasSearched && results.length === 0}
        <div class="no-results">No results found. Try adjusting your search.</div>
      {:else if results.length > 0}
        <div class="results">
          <h4>Results</h4>
          <ul class="result-list">
            {#each results as result}
              <li class="result-item">
                <button class="result-btn" on:click={() => handleSelect(result)}>
                  <div class="result-info">
                    <span class="result-title">{result.name}</span>
                    <span class="result-artist">{result.artists.join(', ')}</span>
                    <span class="result-album">{result.album}</span>
                  </div>
                  <span class="select-icon">+</span>
                </button>
              </li>
            {/each}
          </ul>
        </div>
      {/if}
    </div>
  </div>
</div>

<style>
  .modal-backdrop {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
  }

  .modal {
    background: white;
    border-radius: 12px;
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
    width: 90%;
    max-width: 500px;
    max-height: 80vh;
    display: flex;
    flex-direction: column;
  }

  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem 1.5rem;
    border-bottom: 1px solid #e5e7eb;
  }

  .modal-header h3 {
    margin: 0;
    font-size: 1.25rem;
    color: #1a1a2e;
  }

  .close-btn {
    background: none;
    border: none;
    font-size: 1.5rem;
    color: #666;
    cursor: pointer;
    padding: 0;
    line-height: 1;
  }

  .close-btn:hover {
    color: #1a1a2e;
  }

  .modal-body {
    padding: 1.5rem;
    overflow-y: auto;
  }

  .search-form {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    margin-bottom: 1rem;
  }

  .form-row {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .form-row label {
    font-size: 0.75rem;
    font-weight: 600;
    color: #666;
    text-transform: uppercase;
  }

  .form-row input {
    padding: 0.5rem 0.75rem;
    border: 1px solid #e5e7eb;
    border-radius: 6px;
    font-size: 1rem;
    font-family: inherit;
  }

  .form-row input:focus {
    outline: none;
    border-color: #1db954;
    box-shadow: 0 0 0 3px rgba(29, 185, 84, 0.15);
  }

  .btn-search {
    background: #1db954;
    color: white;
    border: none;
    padding: 0.75rem 1rem;
    border-radius: 6px;
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.15s;
    margin-top: 0.5rem;
  }

  .btn-search:hover:not(:disabled) {
    background: #1aa34a;
  }

  .btn-search:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .error {
    background: #fee2e2;
    color: #dc2626;
    padding: 0.75rem;
    border-radius: 6px;
    font-size: 0.875rem;
    margin-bottom: 1rem;
  }

  .loading, .no-results {
    text-align: center;
    color: #666;
    padding: 2rem 1rem;
  }

  .results h4 {
    margin: 0 0 0.75rem 0;
    font-size: 0.875rem;
    color: #666;
    text-transform: uppercase;
  }

  .result-list {
    list-style: none;
    padding: 0;
    margin: 0;
  }

  .result-item {
    border-bottom: 1px solid #f0f0f0;
  }

  .result-item:last-child {
    border-bottom: none;
  }

  .result-btn {
    width: 100%;
    background: none;
    border: none;
    padding: 0.75rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    cursor: pointer;
    text-align: left;
    transition: background 0.15s;
    border-radius: 6px;
  }

  .result-btn:hover {
    background: #f0fdf4;
  }

  .result-info {
    display: flex;
    flex-direction: column;
    gap: 0.125rem;
    overflow: hidden;
  }

  .result-title {
    font-weight: 600;
    color: #1a1a2e;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .result-artist {
    font-size: 0.875rem;
    color: #666;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .result-album {
    font-size: 0.75rem;
    color: #999;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .select-icon {
    flex-shrink: 0;
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #1db954;
    color: white;
    border-radius: 50%;
    font-weight: bold;
    font-size: 1rem;
  }
</style>
