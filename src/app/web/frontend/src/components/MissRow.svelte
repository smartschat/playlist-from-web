<script lang="ts">
  import type { Miss } from '../lib/types';
  import { createEventDispatcher } from 'svelte';

  export let miss: Miss;
  export let index: number;

  const dispatch = createEventDispatcher<{
    search: Miss;
    ignore: Miss;
  }>();

  function handleSearch() {
    dispatch('search', miss);
  }

  function handleIgnore() {
    dispatch('ignore', miss);
  }
</script>

<tr class="miss-row">
  <td class="num">{index + 1}</td>
  <td class="block">{miss.block}</td>
  <td class="artist">{miss.artist}</td>
  <td class="title">{miss.title}</td>
  <td class="actions">
    <button class="btn-search" on:click={handleSearch} title="Search on Spotify">
      Search
    </button>
    <button class="btn-ignore" on:click={handleIgnore} title="Ignore this miss">
      Ignore
    </button>
  </td>
</tr>

<style>
  .miss-row {
    transition: background-color 0.15s;
  }

  .miss-row:hover {
    background: #fef3c7;
  }

  td {
    padding: 0.625rem 1rem;
    border-bottom: 1px solid #f0f0f0;
  }

  .num {
    width: 3rem;
    color: #999;
    text-align: center;
  }

  .block {
    color: #666;
    font-size: 0.875rem;
    max-width: 150px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .artist {
    font-weight: 500;
  }

  .title {
    color: #333;
  }

  .actions {
    white-space: nowrap;
    text-align: right;
  }

  .btn-search, .btn-ignore {
    padding: 0.375rem 0.75rem;
    border: none;
    border-radius: 4px;
    font-size: 0.75rem;
    cursor: pointer;
    transition: background 0.15s, transform 0.15s;
  }

  .btn-search {
    background: #1db954;
    color: white;
    margin-right: 0.5rem;
  }

  .btn-search:hover {
    background: #1aa34a;
  }

  .btn-ignore {
    background: #e5e7eb;
    color: #666;
  }

  .btn-ignore:hover {
    background: #d1d5db;
  }
</style>
