<script>
  import Call from "./Call.svelte"
  import { state } from "./hit"

  state.initialize()
</script>

{#if $state.ready}
  <Call />
{:else if $state.failure}
  <div class="text-bold flex h-screen w-screen items-center justify-center text-xl italic text-error">
    Failure: {$state.failure}
  </div>
{:else}
  <div class="flex h-screen w-screen items-center justify-center text-xl italic">Loading...</div>
{/if}
