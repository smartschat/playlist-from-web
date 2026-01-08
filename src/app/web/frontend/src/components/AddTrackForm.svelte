<script lang="ts">
  import type { Track } from '../lib/types';
  import { createEventDispatcher } from 'svelte';

  const dispatch = createEventDispatcher<{
    add: Track;
    cancel: void;
  }>();

  let artist = '';
  let title = '';
  let album = '';

  function handleSubmit() {
    if (!artist.trim() || !title.trim()) return;

    const track: Track = {
      artist: artist.trim(),
      title: title.trim(),
      album: album.trim() || null,
      source_line: null
    };

    dispatch('add', track);

    // Reset form
    artist = '';
    title = '';
    album = '';
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') {
      dispatch('cancel');
    }
  }
</script>

<form class="add-track-form" on:submit|preventDefault={handleSubmit} on:keydown={handleKeydown}>
  <div class="form-row">
    <input
      type="text"
      placeholder="Artist *"
      bind:value={artist}
      class="input artist-input"
      autofocus
      required
    />
    <input
      type="text"
      placeholder="Title *"
      bind:value={title}
      class="input title-input"
      required
    />
    <input
      type="text"
      placeholder="Album (optional)"
      bind:value={album}
      class="input album-input"
    />
  </div>
  <div class="form-actions">
    <button type="button" class="btn btn-cancel" on:click={() => dispatch('cancel')}>
      Cancel
    </button>
    <button type="submit" class="btn btn-add" disabled={!artist.trim() || !title.trim()}>
      Add Track
    </button>
  </div>
</form>

<style>
  .add-track-form {
    background: #fff;
    border: 2px solid #1db954;
    border-radius: 8px;
    padding: 1rem;
  }

  .form-row {
    display: flex;
    gap: 0.75rem;
    margin-bottom: 1rem;
  }

  .input {
    flex: 1;
    padding: 0.625rem 0.875rem;
    border: 1px solid #e0e0e0;
    border-radius: 6px;
    font-size: 0.875rem;
    font-family: inherit;
    transition: border-color 0.15s, box-shadow 0.15s;
  }

  .input:focus {
    outline: none;
    border-color: #1db954;
    box-shadow: 0 0 0 3px rgba(29, 185, 84, 0.1);
  }

  .input::placeholder {
    color: #9ca3af;
  }

  .artist-input {
    flex: 1.2;
  }

  .title-input {
    flex: 1.2;
  }

  .album-input {
    flex: 1;
  }

  .form-actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.5rem;
  }

  .btn {
    padding: 0.5rem 1rem;
    border-radius: 6px;
    font-size: 0.875rem;
    font-weight: 500;
    cursor: pointer;
    transition: background 0.15s, opacity 0.15s;
  }

  .btn-cancel {
    background: #f3f4f6;
    border: 1px solid #e5e7eb;
    color: #4b5563;
  }

  .btn-cancel:hover {
    background: #e5e7eb;
  }

  .btn-add {
    background: #1db954;
    border: none;
    color: #fff;
  }

  .btn-add:hover:not(:disabled) {
    background: #1aa34a;
  }

  .btn-add:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
</style>
