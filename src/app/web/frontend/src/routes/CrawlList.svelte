<script lang="ts">
  import { onMount } from 'svelte';
  import { listCrawls } from '../lib/api';
  import type { CrawlSummary } from '../lib/types';

  let crawls: CrawlSummary[] = [];
  let loading = true;
  let error: string | null = null;

  onMount(async () => {
    try {
      crawls = await listCrawls();
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to load crawls';
    } finally {
      loading = false;
    }
  });

  function formatDate(dateStr: string | null): string {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  function getStatusColor(crawl: CrawlSummary): string {
    if (crawl.failed_count > 0) return 'warn';
    if (crawl.success_count > 0) return 'success';
    return '';
  }

  function formatCost(cost: number | null): string {
    if (cost === null) return '-';
    return `$${cost.toFixed(4)}`;
  }
</script>

<div class="crawl-list-page">
  <header class="page-header">
    <nav class="breadcrumb">
      <a href="#/">Dashboard</a>
      <span>/</span>
      <span>Crawls</span>
    </nav>
    <h1>Crawl Results</h1>
    <p class="subtitle">View results from crawled index pages</p>
  </header>

  {#if loading}
    <div class="loading">Loading crawls...</div>
  {:else if error}
    <div class="error">{error}</div>
  {:else if crawls.length === 0}
    <div class="empty">
      <p>No crawl results found.</p>
      <p class="hint">Run <code>uv run python -m app crawl &lt;url&gt;</code> to crawl an index page.</p>
    </div>
  {:else}
    <div class="crawl-grid">
      {#each crawls as crawl (crawl.slug)}
        <article class="crawl-card">
          <header>
            <h2 title={crawl.index_url}>{crawl.index_url || crawl.slug}</h2>
          </header>

          <div class="stats">
            <div class="stat">
              <span class="value">{crawl.link_count}</span>
              <span class="label">link{crawl.link_count !== 1 ? 's' : ''}</span>
            </div>
            <div class="stat">
              <span class="value success">{crawl.success_count}</span>
              <span class="label">success</span>
            </div>
            <div class="stat">
              <span class="value">{crawl.skipped_count}</span>
              <span class="label">skipped</span>
            </div>
            <div class="stat">
              <span class="value {crawl.failed_count > 0 ? 'warn' : ''}">{crawl.failed_count}</span>
              <span class="label">failed</span>
            </div>
          </div>

          <footer>
            <div class="footer-meta">
              <time>{formatDate(crawl.crawled_at)}</time>
              {#if crawl.llm_cost_usd !== null}
                <span class="cost">LLM: {formatCost(crawl.llm_cost_usd)}</span>
              {/if}
            </div>
            <a href="#/crawl/{crawl.slug}" class="btn">View Details</a>
          </footer>
        </article>
      {/each}
    </div>
  {/if}
</div>

<style>
  .crawl-list-page {
    max-width: 1200px;
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

  .loading, .error, .empty {
    text-align: center;
    padding: 4rem 2rem;
    color: #6b7280;
  }

  .error {
    color: #dc2626;
  }

  .empty .hint {
    margin-top: 0.5rem;
    font-size: 0.875rem;
  }

  .empty code {
    background: #f3f4f6;
    padding: 0.125rem 0.375rem;
    border-radius: 4px;
    font-size: 0.8125rem;
  }

  .crawl-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
    gap: 1.25rem;
  }

  .crawl-card {
    background: #fff;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 1.25rem;
    transition: box-shadow 0.2s, transform 0.2s;
  }

  .crawl-card:hover {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    transform: translateY(-2px);
  }

  .crawl-card header {
    margin-bottom: 1rem;
  }

  .crawl-card h2 {
    margin: 0;
    font-size: 0.9375rem;
    font-weight: 600;
    color: #1a1a2e;
    line-height: 1.4;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .stats {
    display: flex;
    gap: 1.5rem;
    margin-bottom: 1rem;
    padding: 0.75rem 0;
  }

  .stat {
    display: flex;
    flex-direction: column;
  }

  .stat .value {
    font-size: 1.25rem;
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

  .stat .label {
    font-size: 0.6875rem;
    color: #9ca3af;
    margin-top: 0.25rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .crawl-card footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-top: 1rem;
    border-top: 1px solid #f3f4f6;
  }

  .footer-meta {
    display: flex;
    flex-direction: column;
    gap: 0.125rem;
  }

  .crawl-card time {
    font-size: 0.8125rem;
    color: #9ca3af;
  }

  .cost {
    font-size: 0.75rem;
    color: #6b7280;
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
