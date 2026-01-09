<script lang="ts">
  import { onMount } from 'svelte';
  import Dashboard from './routes/Dashboard.svelte';
  import PlaylistDetail from './routes/PlaylistDetail.svelte';
  import Import from './routes/Import.svelte';
  import CrawlList from './routes/CrawlList.svelte';
  import CrawlDetail from './routes/CrawlDetail.svelte';

  let currentRoute = '';
  let routeParams: Record<string, string> = {};

  function parseHash() {
    const hash = window.location.hash.slice(1) || '/';

    // Match /playlist/:slug
    const playlistMatch = hash.match(/^\/playlist\/(.+)$/);
    if (playlistMatch) {
      currentRoute = 'playlist';
      routeParams = { slug: decodeURIComponent(playlistMatch[1]) };
      return;
    }

    // Match /import
    if (hash === '/import') {
      currentRoute = 'import';
      routeParams = {};
      return;
    }

    // Match /crawls
    if (hash === '/crawls') {
      currentRoute = 'crawls';
      routeParams = {};
      return;
    }

    // Match /crawl/:slug
    const crawlMatch = hash.match(/^\/crawl\/(.+)$/);
    if (crawlMatch) {
      currentRoute = 'crawl';
      routeParams = { slug: decodeURIComponent(crawlMatch[1]) };
      return;
    }

    // Default to dashboard
    currentRoute = 'dashboard';
    routeParams = {};
  }

  onMount(() => {
    parseHash();
    window.addEventListener('hashchange', parseHash);
    return () => window.removeEventListener('hashchange', parseHash);
  });
</script>

<main>
  {#if currentRoute === 'playlist'}
    <PlaylistDetail slug={routeParams.slug} />
  {:else if currentRoute === 'import'}
    <Import />
  {:else if currentRoute === 'crawls'}
    <CrawlList />
  {:else if currentRoute === 'crawl'}
    <CrawlDetail slug={routeParams.slug} />
  {:else}
    <Dashboard />
  {/if}
</main>

<style>
  :global(body) {
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
    background: #f9fafb;
    color: #1a1a2e;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
  }

  main {
    min-height: 100vh;
  }
</style>
