<script lang="ts">
  import type { TrackBlock, Track } from '../lib/types';
  import { createEventDispatcher } from 'svelte';
  import { dndzone } from 'svelte-dnd-action';
  import TrackRow from './TrackRow.svelte';
  import AddTrackForm from './AddTrackForm.svelte';

  export let block: TrackBlock;
  export let blockIndex: number;
  export let editMode: boolean = false;

  const dispatch = createEventDispatcher<{
    update: TrackBlock;
    delete: void;
  }>();

  let editingTitle = false;
  let editingContext = false;
  let titleValue = '';
  let contextValue = '';
  let showAddForm = false;

  // For drag-and-drop, we need items with IDs
  $: tracksWithIds = block.tracks.map((t, i) => ({ ...t, id: i }));

  function startEditTitle() {
    if (!editMode) return;
    editingTitle = true;
    titleValue = block.title;
  }

  function saveTitle() {
    if (editingTitle) {
      dispatch('update', { ...block, title: titleValue });
      editingTitle = false;
    }
  }

  function startEditContext() {
    if (!editMode) return;
    editingContext = true;
    contextValue = block.context || '';
  }

  function saveContext() {
    if (editingContext) {
      dispatch('update', { ...block, context: contextValue || null });
      editingContext = false;
    }
  }

  function handleKeydown(e: KeyboardEvent, save: () => void, cancel: () => void) {
    if (e.key === 'Enter') {
      e.preventDefault();
      save();
    } else if (e.key === 'Escape') {
      cancel();
    }
  }

  function handleTrackUpdate(index: number, updatedTrack: Track) {
    // Strip the transient dnd id if present
    const { id, ...trackWithoutId } = updatedTrack as Track & { id?: number };
    const newTracks = [...block.tracks];
    newTracks[index] = trackWithoutId as Track;
    dispatch('update', { ...block, tracks: newTracks });
  }

  function handleTrackDelete(index: number) {
    const newTracks = block.tracks.filter((_, i) => i !== index);
    dispatch('update', { ...block, tracks: newTracks });
  }

  function handleAddTrack(track: Track) {
    const newTracks = [...block.tracks, track];
    dispatch('update', { ...block, tracks: newTracks });
    showAddForm = false;
  }

  function handleDndConsider(e: CustomEvent<{ items: (Track & { id: number })[] }>) {
    tracksWithIds = e.detail.items;
  }

  function handleDndFinalize(e: CustomEvent<{ items: (Track & { id: number })[] }>) {
    // Remove the id property when saving back
    const newTracks = e.detail.items.map(({ id, ...track }) => track as Track);
    dispatch('update', { ...block, tracks: newTracks });
  }

  function handleDeleteBlock() {
    dispatch('delete');
  }
</script>

<section class="block" class:edit-mode={editMode}>
  <header class="block-header">
    <div class="header-content">
      {#if editingTitle}
        <input
          type="text"
          class="title-input"
          bind:value={titleValue}
          on:keydown={(e) => handleKeydown(e, saveTitle, () => editingTitle = false)}
          on:blur={saveTitle}
          autofocus
        />
      {:else}
        <h2 on:dblclick={startEditTitle} class:editable={editMode}>
          {block.title || `Block ${blockIndex + 1}`}
        </h2>
      {/if}

      {#if editMode}
        <button class="delete-block-btn" on:click={handleDeleteBlock} title="Delete block">
          &times;
        </button>
      {/if}
    </div>

    {#if editingContext}
      <textarea
        class="context-input"
        bind:value={contextValue}
        on:keydown={(e) => {
          if (e.key === 'Escape') {
            editingContext = false;
          }
        }}
        on:blur={saveContext}
        placeholder="Add context..."
        autofocus
      ></textarea>
    {:else if block.context || editMode}
      <p class="context" class:editable={editMode} class:empty={!block.context} on:dblclick={startEditContext}>
        {block.context || (editMode ? 'Click to add context...' : '')}
      </p>
    {/if}

    <span class="track-count">{block.tracks.length} track{block.tracks.length !== 1 ? 's' : ''}</span>
  </header>

  <table class="tracks-table">
    <thead>
      <tr>
        {#if editMode}
          <th class="drag-col"></th>
        {/if}
        <th class="num">#</th>
        <th>Artist</th>
        <th>Title</th>
        <th>Album</th>
        {#if editMode}
          <th class="actions-col"></th>
        {/if}
      </tr>
    </thead>
    <tbody
      use:dndzone={{
        items: tracksWithIds,
        flipDurationMs: 200,
        dropTargetStyle: {},
        dragDisabled: !editMode
      }}
      on:consider={handleDndConsider}
      on:finalize={handleDndFinalize}
    >
      {#each tracksWithIds as track, index (track.id)}
        <TrackRow
          track={track}
          {index}
          {editMode}
          on:update={(e) => handleTrackUpdate(index, e.detail)}
          on:delete={() => handleTrackDelete(index)}
        />
      {/each}
    </tbody>
  </table>

  {#if editMode}
    <div class="add-track-section">
      {#if showAddForm}
        <AddTrackForm
          on:add={(e) => handleAddTrack(e.detail)}
          on:cancel={() => showAddForm = false}
        />
      {:else}
        <button class="add-track-btn" on:click={() => showAddForm = true}>
          + Add Track
        </button>
      {/if}
    </div>
  {/if}
</section>

<style>
  .block {
    background: #fff;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    margin-bottom: 1.5rem;
    overflow: hidden;
  }

  .block.edit-mode {
    border-color: #1db954;
  }

  .block-header {
    padding: 1rem;
    background: #f8f9fa;
    border-bottom: 1px solid #e0e0e0;
  }

  .header-content {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 0.5rem;
  }

  .block-header h2 {
    margin: 0;
    font-size: 1.125rem;
    flex: 1;
  }

  .block-header h2.editable {
    cursor: pointer;
    padding: 0.25rem 0.5rem;
    margin: -0.25rem -0.5rem;
    border-radius: 4px;
    transition: background 0.15s;
  }

  .block-header h2.editable:hover {
    background: #e8f4fd;
  }

  .title-input {
    flex: 1;
    padding: 0.375rem 0.5rem;
    border: 2px solid #1db954;
    border-radius: 4px;
    font-size: 1.125rem;
    font-weight: bold;
    font-family: inherit;
  }

  .title-input:focus {
    outline: none;
    box-shadow: 0 0 0 3px rgba(29, 185, 84, 0.2);
  }

  .delete-block-btn {
    background: none;
    border: none;
    color: #dc2626;
    font-size: 1.5rem;
    cursor: pointer;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    line-height: 1;
    opacity: 0.6;
    transition: opacity 0.15s, background 0.15s;
  }

  .delete-block-btn:hover {
    opacity: 1;
    background: #fee2e2;
  }

  .context {
    margin: 0.5rem 0 0;
    font-size: 0.875rem;
    color: #666;
  }

  .context.editable {
    cursor: pointer;
    padding: 0.25rem 0.5rem;
    margin-left: -0.5rem;
    margin-right: -0.5rem;
    border-radius: 4px;
    transition: background 0.15s;
  }

  .context.editable:hover {
    background: #e8f4fd;
  }

  .context.empty {
    color: #999;
    font-style: italic;
  }

  .context-input {
    width: 100%;
    margin-top: 0.5rem;
    padding: 0.375rem 0.5rem;
    border: 2px solid #1db954;
    border-radius: 4px;
    font-size: 0.875rem;
    font-family: inherit;
    resize: vertical;
    min-height: 3rem;
  }

  .context-input:focus {
    outline: none;
    box-shadow: 0 0 0 3px rgba(29, 185, 84, 0.2);
  }

  .track-count {
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

  .tracks-table .num,
  .tracks-table .drag-col,
  .tracks-table .actions-col {
    width: 3rem;
    text-align: center;
  }

  .tracks-table .drag-col {
    width: 2rem;
  }

  .add-track-section {
    padding: 1rem;
    border-top: 1px solid #f0f0f0;
    background: #fafafa;
  }

  .add-track-btn {
    background: none;
    border: 2px dashed #ccc;
    color: #666;
    padding: 0.75rem 1.5rem;
    border-radius: 8px;
    font-size: 0.875rem;
    cursor: pointer;
    width: 100%;
    transition: border-color 0.15s, color 0.15s, background 0.15s;
  }

  .add-track-btn:hover {
    border-color: #1db954;
    color: #1db954;
    background: #f0fdf4;
  }
</style>
