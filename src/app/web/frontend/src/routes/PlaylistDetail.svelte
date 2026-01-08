<script lang="ts">
  import { onMount } from 'svelte';
  import { getPlaylist } from '../lib/api';
  import type { ParsedPlaylist } from '../lib/types';

  export let slug: string;

  let playlist: ParsedPlaylist | null = null;
  let loading = true;
  let error: string | null = null;

  onMount(async () => {
    try {
      playlist = await getPlaylist(slug);
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to load playlist';
    } finally {
      loading = false;
    }
  });

  function getTotalTracks(playlist: ParsedPlaylist): number {
    return playlist.blocks.reduce((sum, block) => sum + block.tracks.length, 0);
  }
</script>

<div class="playlist-detail">
  <nav class="breadcrumb">
    <a href="#/">Dashboard</a>
    <span class="separator">/</span>
    <span class="current">{playlist?.source_name || slug}</span>
  </nav>

  {#if loading}
    <div class="loading">Loading playlist...</div>
  {:else if error}
    <div class="error">{error}</div>
  {:else if playlist}
    <header>
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
    </header>

    <div class="blocks">
      {#each playlist.blocks as block, blockIndex}
        <section class="block">
          <header class="block-header">
            <h2>{block.title || `Block ${blockIndex + 1}`}</h2>
            {#if block.context}
              <p class="context">{block.context}</p>
            {/if}
            <span class="track-count">{block.tracks.length} track{block.tracks.length !== 1 ? 's' : ''}</span>
          </header>

          <table class="tracks-table">
            <thead>
              <tr>
                <th class="num">#</th>
                <th>Artist</th>
                <th>Title</th>
                <th>Album</th>
              </tr>
            </thead>
            <tbody>
              {#each block.tracks as track, trackIndex}
                <tr>
                  <td class="num">{trackIndex + 1}</td>
                  <td class="artist">{track.artist}</td>
                  <td class="title">{track.title}</td>
                  <td class="album">{track.album || '-'}</td>
                </tr>
              {/each}
            </tbody>
          </table>
        </section>
      {/each}
    </div>
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
    color: #007bff;
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

  header h1 {
    margin: 0 0 0.5rem;
    font-size: 1.75rem;
  }

  .meta {
    color: #666;
    margin: 0 0 0.5rem;
  }

  .source-link {
    font-size: 0.875rem;
    color: #007bff;
    text-decoration: none;
  }

  .source-link:hover {
    text-decoration: underline;
  }

  .loading, .error {
    text-align: center;
    padding: 3rem;
    color: #666;
  }

  .error {
    color: #c00;
  }

  .blocks {
    margin-top: 2rem;
  }

  .block {
    background: #fff;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    margin-bottom: 1.5rem;
    overflow: hidden;
  }

  .block-header {
    padding: 1rem;
    background: #f8f9fa;
    border-bottom: 1px solid #e0e0e0;
  }

  .block-header h2 {
    margin: 0;
    font-size: 1.125rem;
  }

  .block-header .context {
    margin: 0.5rem 0 0;
    font-size: 0.875rem;
    color: #666;
  }

  .block-header .track-count {
    display: inline-block;
    margin-top: 0.5rem;
    font-size: 0.75rem;
    color: #888;
  }

  .tracks-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.875rem;
  }

  .tracks-table th {
    text-align: left;
    padding: 0.75rem 1rem;
    border-bottom: 1px solid #e0e0e0;
    font-weight: 600;
    color: #666;
    background: #fafafa;
  }

  .tracks-table td {
    padding: 0.625rem 1rem;
    border-bottom: 1px solid #f0f0f0;
  }

  .tracks-table tr:last-child td {
    border-bottom: none;
  }

  .tracks-table tr:hover {
    background: #f8f9fa;
  }

  .tracks-table .num {
    width: 3rem;
    color: #999;
    text-align: center;
  }

  .tracks-table .artist {
    font-weight: 500;
  }

  .tracks-table .album {
    color: #666;
  }
</style>
