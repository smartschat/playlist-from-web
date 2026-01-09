<script lang="ts">
  import { previewImport, executeImport } from '../lib/api';
  import type { ImportPreviewResponse, ImportExecuteResponse } from '../lib/types';

  let url = '';
  let forceRefetch = false;
  let loading = false;
  let error: string | null = null;

  let previewResult: ImportPreviewResponse | null = null;
  let importResult: ImportExecuteResponse | null = null;

  async function handlePreview() {
    if (!url.trim()) {
      error = 'Please enter a URL';
      return;
    }

    loading = true;
    error = null;
    previewResult = null;
    importResult = null;

    try {
      previewResult = await previewImport(url.trim(), forceRefetch);
    } catch (e) {
      error = e instanceof Error ? e.message : 'Preview failed';
    } finally {
      loading = false;
    }
  }

  async function handleImport() {
    if (!url.trim()) {
      error = 'Please enter a URL';
      return;
    }

    loading = true;
    error = null;
    importResult = null;

    try {
      importResult = await executeImport(url.trim(), forceRefetch);
    } catch (e) {
      error = e instanceof Error ? e.message : 'Import failed';
    } finally {
      loading = false;
    }
  }

  function reset() {
    previewResult = null;
    importResult = null;
    error = null;
  }
</script>

<div class="import-page">
  <header class="page-header">
    <nav class="breadcrumb">
      <a href="#/">Dashboard</a>
      <span>/</span>
      <span>Import</span>
    </nav>
    <h1>Import URL</h1>
    <p class="subtitle">Parse and import playlists from a web page</p>
  </header>

  <div class="import-form">
    <div class="form-group">
      <label for="url">URL</label>
      <input
        id="url"
        type="url"
        placeholder="https://example.com/playlist"
        bind:value={url}
        on:input={reset}
        disabled={loading}
      />
    </div>

    <div class="form-group checkbox">
      <label>
        <input type="checkbox" bind:checked={forceRefetch} disabled={loading} />
        Force re-fetch (ignore cache)
      </label>
    </div>

    <div class="actions">
      <button class="btn btn-secondary" on:click={handlePreview} disabled={loading || !url.trim()}>
        {#if loading && !importResult}
          Parsing...
        {:else}
          Preview
        {/if}
      </button>
      <button class="btn btn-primary" on:click={handleImport} disabled={loading || !url.trim()}>
        {#if loading && importResult === null && previewResult !== null}
          Importing...
        {:else}
          Import to Spotify
        {/if}
      </button>
    </div>
  </div>

  {#if error}
    <div class="error-banner">
      <strong>Error:</strong> {error}
    </div>
  {/if}

  {#if loading && !previewResult && !importResult}
    <div class="loading">
      <div class="spinner"></div>
      <p>Processing URL...</p>
    </div>
  {/if}

  {#if previewResult && !importResult}
    <div class="preview-result">
      <h2>Preview Result</h2>
      <div class="summary">
        <div class="stat">
          <span class="value">{previewResult.block_count}</span>
          <span class="label">block{previewResult.block_count !== 1 ? 's' : ''}</span>
        </div>
        <div class="stat">
          <span class="value">{previewResult.track_count}</span>
          <span class="label">track{previewResult.track_count !== 1 ? 's' : ''}</span>
        </div>
      </div>

      {#if previewResult.source_name}
        <p class="source-name"><strong>Source:</strong> {previewResult.source_name}</p>
      {/if}

      <div class="blocks-preview">
        {#each previewResult.blocks as block, idx}
          <div class="block-card">
            <h3>{block.title || `Block ${idx + 1}`}</h3>
            {#if block.context}
              <p class="context">{block.context}</p>
            {/if}
            <p class="track-count">{block.tracks.length} track{block.tracks.length !== 1 ? 's' : ''}</p>
            <ul class="track-list">
              {#each block.tracks.slice(0, 5) as track}
                <li>{track.artist} - {track.title}</li>
              {/each}
              {#if block.tracks.length > 5}
                <li class="more">...and {block.tracks.length - 5} more</li>
              {/if}
            </ul>
          </div>
        {/each}
      </div>

      <div class="preview-actions">
        <button class="btn btn-primary" on:click={handleImport} disabled={loading}>
          {#if loading}
            Importing...
          {:else}
            Import to Spotify
          {/if}
        </button>
      </div>
    </div>
  {/if}

  {#if importResult}
    <div class="import-result success">
      <h2>Import Complete</h2>
      <div class="summary">
        <div class="stat">
          <span class="value">{importResult.playlist_count}</span>
          <span class="label">playlist{importResult.playlist_count !== 1 ? 's' : ''} created</span>
        </div>
        <div class="stat">
          <span class="value {importResult.miss_count > 0 ? 'warn' : ''}">{importResult.miss_count}</span>
          <span class="label">miss{importResult.miss_count !== 1 ? 'es' : ''}</span>
        </div>
        {#if importResult.has_master}
          <div class="stat">
            <span class="value">1</span>
            <span class="label">master playlist</span>
          </div>
        {/if}
      </div>

      <div class="result-actions">
        <a href="#/playlist/{importResult.slug}" class="btn btn-primary">View Playlist</a>
        <button class="btn btn-secondary" on:click={() => { url = ''; reset(); }}>Import Another</button>
      </div>
    </div>
  {/if}
</div>

<style>
  .import-page {
    max-width: 900px;
    margin: 0 auto;
    padding: 2rem;
  }

  .page-header {
    margin-bottom: 2rem;
  }

  .breadcrumb {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.875rem;
    color: #6b7280;
    margin-bottom: 0.75rem;
  }

  .breadcrumb a {
    color: #1db954;
    text-decoration: none;
  }

  .breadcrumb a:hover {
    text-decoration: underline;
  }

  .page-header h1 {
    margin: 0;
    font-size: 1.75rem;
    font-weight: 700;
    color: #1a1a2e;
  }

  .subtitle {
    color: #6b7280;
    margin: 0.375rem 0 0;
    font-size: 0.9375rem;
  }

  .import-form {
    background: #fff;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1.5rem;
  }

  .form-group {
    margin-bottom: 1rem;
  }

  .form-group label {
    display: block;
    font-size: 0.875rem;
    font-weight: 500;
    color: #374151;
    margin-bottom: 0.375rem;
  }

  .form-group.checkbox label {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    cursor: pointer;
  }

  .form-group input[type="url"] {
    width: 100%;
    padding: 0.75rem 1rem;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    font-size: 1rem;
    transition: border-color 0.15s, box-shadow 0.15s;
  }

  .form-group input[type="url"]:focus {
    outline: none;
    border-color: #1db954;
    box-shadow: 0 0 0 3px rgba(29, 185, 84, 0.1);
  }

  .form-group input[type="checkbox"] {
    width: 1rem;
    height: 1rem;
    accent-color: #1db954;
  }

  .actions {
    display: flex;
    gap: 0.75rem;
    margin-top: 1.25rem;
  }

  .btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0.75rem 1.5rem;
    border: none;
    border-radius: 8px;
    font-size: 0.9375rem;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.15s, opacity 0.15s;
  }

  .btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .btn-primary {
    background: #1db954;
    color: #fff;
  }

  .btn-primary:hover:not(:disabled) {
    background: #1aa34a;
  }

  .btn-secondary {
    background: #f3f4f6;
    color: #374151;
  }

  .btn-secondary:hover:not(:disabled) {
    background: #e5e7eb;
  }

  .error-banner {
    background: #fef2f2;
    border: 1px solid #fecaca;
    color: #dc2626;
    padding: 1rem;
    border-radius: 8px;
    margin-bottom: 1.5rem;
  }

  .loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1rem;
    padding: 3rem;
    color: #6b7280;
  }

  .spinner {
    width: 2rem;
    height: 2rem;
    border: 3px solid #e5e7eb;
    border-top-color: #1db954;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .preview-result, .import-result {
    background: #fff;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 1.5rem;
  }

  .import-result.success {
    border-color: #86efac;
    background: #f0fdf4;
  }

  .preview-result h2, .import-result h2 {
    margin: 0 0 1rem;
    font-size: 1.25rem;
    font-weight: 600;
  }

  .summary {
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

  .source-name {
    font-size: 0.9375rem;
    color: #4b5563;
    margin: 0 0 1rem;
  }

  .blocks-preview {
    display: grid;
    gap: 1rem;
    margin-top: 1rem;
  }

  .block-card {
    background: #f9fafb;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 1rem;
  }

  .block-card h3 {
    margin: 0 0 0.5rem;
    font-size: 1rem;
    font-weight: 600;
  }

  .block-card .context {
    font-size: 0.875rem;
    color: #6b7280;
    margin: 0 0 0.5rem;
  }

  .block-card .track-count {
    font-size: 0.75rem;
    color: #9ca3af;
    margin: 0 0 0.5rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .track-list {
    margin: 0;
    padding: 0;
    list-style: none;
    font-size: 0.875rem;
  }

  .track-list li {
    padding: 0.25rem 0;
    color: #4b5563;
    border-bottom: 1px solid #f3f4f6;
  }

  .track-list li:last-child {
    border-bottom: none;
  }

  .track-list li.more {
    color: #9ca3af;
    font-style: italic;
  }

  .preview-actions, .result-actions {
    display: flex;
    gap: 0.75rem;
    margin-top: 1.5rem;
    padding-top: 1rem;
    border-top: 1px solid #e5e7eb;
  }

  .import-result.success .result-actions {
    border-top-color: #86efac;
  }
</style>
