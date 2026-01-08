<script lang="ts">
  import type { Track } from '../lib/types';
  import { createEventDispatcher } from 'svelte';

  export let track: Track;
  export let index: number;
  export let editMode: boolean = false;

  const dispatch = createEventDispatcher<{
    update: Track;
    delete: void;
  }>();

  let editingField: 'artist' | 'title' | 'album' | null = null;
  let editValue = '';

  function startEdit(field: 'artist' | 'title' | 'album') {
    if (!editMode) return;
    editingField = field;
    editValue = field === 'album' ? (track[field] || '') : track[field];
  }

  function cancelEdit() {
    editingField = null;
    editValue = '';
  }

  function saveEdit() {
    if (!editingField) return;

    const updatedTrack = {
      ...track,
      [editingField]: editingField === 'album' && editValue === '' ? null : editValue
    };

    dispatch('update', updatedTrack);
    editingField = null;
    editValue = '';
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter') {
      e.preventDefault();
      saveEdit();
    } else if (e.key === 'Escape') {
      cancelEdit();
    }
  }

  function handleDelete() {
    dispatch('delete');
  }
</script>

<tr class="track-row" class:edit-mode={editMode}>
  {#if editMode}
    <td class="drag-handle">
      <span class="handle">⋮⋮</span>
    </td>
  {/if}
  <td class="num">{index + 1}</td>
  <td class="artist" on:dblclick={() => startEdit('artist')}>
    {#if editingField === 'artist'}
      <input
        type="text"
        bind:value={editValue}
        on:keydown={handleKeydown}
        on:blur={saveEdit}
        autofocus
      />
    {:else}
      <span class:editable={editMode}>{track.artist}</span>
    {/if}
  </td>
  <td class="title" on:dblclick={() => startEdit('title')}>
    {#if editingField === 'title'}
      <input
        type="text"
        bind:value={editValue}
        on:keydown={handleKeydown}
        on:blur={saveEdit}
        autofocus
      />
    {:else}
      <span class:editable={editMode}>{track.title}</span>
    {/if}
  </td>
  <td class="album" on:dblclick={() => startEdit('album')}>
    {#if editingField === 'album'}
      <input
        type="text"
        bind:value={editValue}
        on:keydown={handleKeydown}
        on:blur={saveEdit}
        autofocus
      />
    {:else}
      <span class:editable={editMode}>{track.album || '-'}</span>
    {/if}
  </td>
  {#if editMode}
    <td class="actions">
      <button class="delete-btn" on:click={handleDelete} title="Delete track">
        &times;
      </button>
    </td>
  {/if}
</tr>

<style>
  .track-row {
    transition: background-color 0.15s;
  }

  .track-row:hover {
    background: #f8f9fa;
  }

  .track-row.edit-mode:hover {
    background: #fef9e7;
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

  .artist {
    font-weight: 500;
  }

  .album {
    color: #666;
  }

  .drag-handle {
    width: 2rem;
    cursor: grab;
    text-align: center;
    color: #ccc;
    user-select: none;
  }

  .drag-handle:active {
    cursor: grabbing;
  }

  .handle {
    font-size: 0.875rem;
    letter-spacing: 2px;
  }

  .actions {
    width: 3rem;
    text-align: center;
  }

  .delete-btn {
    background: none;
    border: none;
    color: #dc2626;
    font-size: 1.25rem;
    cursor: pointer;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    line-height: 1;
    opacity: 0.6;
    transition: opacity 0.15s, background 0.15s;
  }

  .delete-btn:hover {
    opacity: 1;
    background: #fee2e2;
  }

  .editable {
    cursor: pointer;
    padding: 0.25rem 0.5rem;
    margin: -0.25rem -0.5rem;
    border-radius: 4px;
    transition: background 0.15s;
  }

  .editable:hover {
    background: #e8f4fd;
  }

  input {
    width: 100%;
    padding: 0.375rem 0.5rem;
    border: 2px solid #1db954;
    border-radius: 4px;
    font-size: inherit;
    font-family: inherit;
    background: #fff;
  }

  input:focus {
    outline: none;
    box-shadow: 0 0 0 3px rgba(29, 185, 84, 0.2);
  }
</style>
