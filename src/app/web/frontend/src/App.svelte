<script lang="ts">
  import { onMount } from 'svelte';
  import Dashboard from './routes/Dashboard.svelte';
  import PlaylistDetail from './routes/PlaylistDetail.svelte';

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
  {:else}
    <Dashboard />
  {/if}
</main>

<style>
  :global(body) {
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
    background: #f5f5f5;
    color: #333;
  }

  main {
    min-height: 100vh;
  }
</style>
