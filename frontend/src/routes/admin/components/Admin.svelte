<script>
  import Call from "./Call.svelte"
  import { state } from "../admin"
  import { onMount } from "svelte"

  export let hits = []
  export let peerjsKey
  let initializing = false

  const selectHit = async (num) => {
    initializing = true
    console.log(peerjsKey)
    await state.initialize(hits[num], peerjsKey)
  }

  // onMount(selectHit)
</script>

{#if $state.hit}
  <Call />
{:else}
  {#each hits as { topic, createdAt }, num}
    <div class="text-xl">
      {num + 1}. {topic} ({createdAt}) &mdash;
      <button class="btn" on:click={() => selectHit(num)} disabled={initializing}>Select</button>
    </div>
  {/each}
{/if}
