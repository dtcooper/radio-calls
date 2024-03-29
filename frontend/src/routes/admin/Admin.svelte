<script>
  import { post } from "$lib/utils"
  import { onMount } from "svelte"

  let ready = false
  let error = false
  let hits = []
  let hit = null

  onMount(async () => {
    const { success, hits: _hits, error: _error } = await post("admin/handshake")
    if (!success) {
      error = _error
      return
    }

    hits = _hits
    ready = true
  })
</script>

<div class="min-h-screen bg-base-200">
  <div class="mx-auto flex min-h-screen max-w-screen-lg flex-col gap-2 bg-base-100 p-3">
    <h1 class="text-center font-mono text-3xl font-bold italic underline">Admin Panel</h1>
    {#if hit}
      Selected: {hit.topic}
    {:else}
      {#each hits as { topic, createdAt }, num}
        <div class="text-xl">
          {num + 1}. {topic} ({createdAt}) &mdash;
          <button class="btn" on:click={() => (hit = hits[num])}>Select</button>
        </div>
      {/each}
    {/if}
    {#if error}
      <div class="alert alert-error">
        <span>Error! {error}</span>
      </div>
    {/if}
  </div>
</div>
