<script>
  import { onMount } from "svelte"
  import HIT from "./HIT.svelte"
  import { state } from "./hit"

  onMount(() => {
    state.initialize()
  })
</script>

{#if $state.ready}
  <HIT />
{:else if $state.failure}
  <div
    class="text-bold flex h-screen w-screen flex-col items-center justify-center gap-3 bg-error p-3 text-xl text-error-content"
  >
    <h1 class="font-mono text-xl font-bold sm:text-2xl">An unexpected failure occurred.</h1>
    <h2 class="bold font-mono text-lg italic sm:text-xl">Please reload the page and try again.</h2>
    <span class="badge badge-neutral badge-sm sm:badge-md md:badge-lg">{$state.failure}</span>
    <button class="btn btn-warning gap-3" on:click={() => window.location.reload()}>Reload...</button>
  </div>
{:else}
  <div class="flex h-screen w-screen items-center justify-center bg-base-200 text-xl italic">Loading...</div>
{/if}
