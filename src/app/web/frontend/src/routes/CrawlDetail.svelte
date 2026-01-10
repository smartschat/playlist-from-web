<script lang="ts">
  import { onMount } from 'svelte';
  import { getCrawl, reprocessCrawlUrl } from '../lib/api';
  import type { CrawlDetail, CrawlProcessedEntry } from '../lib/types';

  export let slug: string;

  let crawl: CrawlDetail | null = null;
  let loading = true;
  let error: string | null = null;
  let reprocessingIdx: number | null = null;

  onMount(async () => {
    await loadCrawl();
  });

  async function loadCrawl() {
    loading = true;
    error = null;
    try {
      crawl = await getCrawl(slug);
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to load crawl';
    } finally {
      loading = false;
    }
  }

  async function handleReprocess(idx: number, devMode: boolean) {
    if (!crawl) return;

    reprocessingIdx = idx;
    try {
      const result = await reprocessCrawlUrl(slug, idx, devMode, true);
      // Update the local state with all returned fields
      crawl.processed[idx] = {
        ...crawl.processed[idx],
        status: result.status as 'success' | 'skipped' | 'failed',
        mode: result.mode,
        artifact: result.artifact,
        error: result.error,
      };
      crawl = crawl; // Trigger reactivity
    } catch (e) {
      // Update with error
      crawl.processed[idx] = {
        ...crawl.processed[idx],
        status: 'failed',
        error: e instanceof Error ? e.message : 'Reprocess failed',
      };
      crawl = crawl;
    } finally {
      reprocessingIdx = null;
    }
  }

  function formatDate(dateStr: string | null): string {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  function getSlugFromArtifact(artifact: string | undefined): string | null {
    if (!artifact) return null;
    // Extract slug from paths like "data/parsed/foo.json" or "data/spotify/foo.json"
    const match = artifact.match(/data\/(?:parsed|spotify)\/(.+)\.json$/);
    return match ? match[1] : null;
  }

  function getStatusBadgeClass(status: string): string {
    switch (status) {
      case 'success': return 'badge-success';
      case 'skipped': return 'badge-skipped';
      case 'failed': return 'badge-failed';
      default: return '';
    }
  }

  $: successCount = crawl?.processed.filter(p => p.status === 'success').length ?? 0;
  $: skippedCount = crawl?.processed.filter(p => p.status === 'skipped').length ?? 0;
  $: failedCount = crawl?.processed.filter(p => p.status === 'failed').length ?? 0;

  function formatCost(cost: number | null | undefined): string {
    if (cost === null || cost === undefined) return '-';
    return `$${cost.toFixed(4)}`;
  }
</script>

<div class="crawl-detail-page">
  <header class="page-header">
    <nav class="breadcrumb">
      <a href="#/">Dashboard</a>
      <span>/</span>
      <a href="#/crawls">Crawls</a>
      <span>/</span>
      <span>{slug}</span>
    </nav>
    <h1>Crawl Details</h1>
    {#if crawl}
      <p class="subtitle">
        <a href={crawl.index_url} target="_blank" rel="noopener">{crawl.index_url}</a>
      </p>
    {/if}
  </header>

  {#if loading}
    <div class="loading">Loading crawl details...</div>
  {:else if error}
    <div class="error">{error}</div>
  {:else if crawl}
    <div class="crawl-summary">
      <div class="stats">
        <div class="stat">
          <span class="value">{crawl.discovered_links.length}</span>
          <span class="label">discovered</span>
        </div>
        <div class="stat">
          <span class="value success">{successCount}</span>
          <span class="label">success</span>
        </div>
        <div class="stat">
          <span class="value">{skippedCount}</span>
          <span class="label">skipped</span>
        </div>
        <div class="stat">
          <span class="value {failedCount > 0 ? 'warn' : ''}">{failedCount}</span>
          <span class="label">failed</span>
        </div>
        {#if crawl.llm_usage}
          <div class="stat">
            <span class="value cost">{formatCost(crawl.llm_usage.cost_usd)}</span>
            <span class="label">LLM cost</span>
          </div>
        {/if}
      </div>
      <p class="crawl-time">Crawled: {formatDate(crawl.crawled_at)}</p>
    </div>

    <div class="processed-list">
      <h2>Processed URLs</h2>
      {#each crawl.processed as entry, idx (idx)}
        <div class="processed-item {entry.status}">
          <div class="item-main">
            <span class="badge {getStatusBadgeClass(entry.status)}">{entry.status}</span>
            <div class="item-info">
              <a href={entry.url} target="_blank" rel="noopener" class="url">{entry.url}</a>
              {#if entry.description}
                <span class="description">{entry.description}</span>
              {/if}
              {#if entry.error}
                <span class="error-text">{entry.error}</span>
              {/if}
              {#if entry.llm_cost_usd !== null && entry.llm_cost_usd !== undefined}
                <span class="entry-cost">LLM: {formatCost(entry.llm_cost_usd)}</span>
              {/if}
            </div>
          </div>
          <div class="item-actions">
            {#if entry.status === 'success' || entry.status === 'skipped'}
              {#if getSlugFromArtifact(entry.artifact)}
                <a href="#/playlist/{getSlugFromArtifact(entry.artifact)}" class="btn btn-small">
                  View
                </a>
              {/if}
            {/if}
            {#if entry.status === 'failed'}
              <button
                class="btn btn-small btn-secondary"
                on:click={() => handleReprocess(idx, true)}
                disabled={reprocessingIdx !== null}
              >
                {#if reprocessingIdx === idx}
                  Processing...
                {:else}
                  Retry (Dev)
                {/if}
              </button>
              <button
                class="btn btn-small"
                on:click={() => handleReprocess(idx, false)}
                disabled={reprocessingIdx !== null}
              >
                {#if reprocessingIdx === idx}
                  Processing...
                {:else}
                  Retry (Import)
                {/if}
              </button>
            {/if}
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

<style>
  .crawl-detail-page {
    max-width: 1000px;
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
    margin: 0.375rem 0 0;
    font-size: 0.9375rem;
  }

  .subtitle a {
    color: #6b7280;
    text-decoration: none;
  }

  .subtitle a:hover {
    color: #1db954;
    text-decoration: underline;
  }

  .loading, .error {
    text-align: center;
    padding: 4rem 2rem;
    color: #6b7280;
  }

  .error {
    color: #dc2626;
  }

  .crawl-summary {
    background: #fff;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 1.25rem;
    margin-bottom: 1.5rem;
  }

  .stats {
    display: flex;
    gap: 2rem;
    margin-bottom: 0.75rem;
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

  .stat .value.success {
    color: #15803d;
  }

  .stat .value.warn {
    color: #d97706;
  }

  .stat .value.cost {
    color: #1a1a2e;
  }

  .stat .label {
    font-size: 0.6875rem;
    color: #9ca3af;
    margin-top: 0.25rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .crawl-time {
    margin: 0;
    font-size: 0.8125rem;
    color: #9ca3af;
  }

  .processed-list {
    background: #fff;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 1.25rem;
  }

  .processed-list h2 {
    margin: 0 0 1rem;
    font-size: 1.125rem;
    font-weight: 600;
  }

  .processed-item {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 1rem;
    padding: 1rem;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    margin-bottom: 0.75rem;
  }

  .processed-item:last-child {
    margin-bottom: 0;
  }

  .processed-item.failed {
    border-color: #fecaca;
    background: #fef2f2;
  }

  .processed-item.success {
    border-color: #bbf7d0;
    background: #f0fdf4;
  }

  .item-main {
    display: flex;
    gap: 0.75rem;
    flex: 1;
    min-width: 0;
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
    height: fit-content;
  }

  .badge-success {
    background: #dcfce7;
    color: #15803d;
  }

  .badge-skipped {
    background: #fef3c7;
    color: #b45309;
  }

  .badge-failed {
    background: #fee2e2;
    color: #dc2626;
  }

  .item-info {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    min-width: 0;
  }

  .url {
    font-size: 0.875rem;
    color: #1a1a2e;
    text-decoration: none;
    word-break: break-all;
  }

  .url:hover {
    color: #1db954;
    text-decoration: underline;
  }

  .description {
    font-size: 0.8125rem;
    color: #6b7280;
  }

  .error-text {
    font-size: 0.8125rem;
    color: #dc2626;
  }

  .entry-cost {
    font-size: 0.75rem;
    color: #6b7280;
  }

  .item-actions {
    display: flex;
    gap: 0.5rem;
    flex-shrink: 0;
  }

  .btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0.5rem 1rem;
    border: none;
    border-radius: 8px;
    font-size: 0.8125rem;
    font-weight: 600;
    cursor: pointer;
    text-decoration: none;
    transition: background 0.15s, opacity 0.15s;
    background: #1db954;
    color: #fff;
  }

  .btn:hover:not(:disabled) {
    background: #1aa34a;
  }

  .btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .btn-small {
    padding: 0.375rem 0.75rem;
    font-size: 0.75rem;
  }

  .btn-secondary {
    background: #f3f4f6;
    color: #374151;
  }

  .btn-secondary:hover:not(:disabled) {
    background: #e5e7eb;
  }
</style>
