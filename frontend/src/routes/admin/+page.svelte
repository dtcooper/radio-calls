<script>
  import { post } from "$lib/utils"
  import { onDestroy, onMount } from "svelte"
  import Admin from "./components/Admin.svelte"
  import { state } from "./admin"

  let ready = false
  let error = false
  let hits = false
  let peerjsKey

  onMount(async () => {
    ;({ success: ready, hits, error, peerjsKey } = await post("admin/handshake"))
  })

  document.documentElement.setAttribute("data-theme", "dark")
</script>

<div class="min-h-screen bg-base-200">
  <div class="mx-auto flex min-h-screen max-w-screen-lg flex-col gap-2 bg-base-100 p-3">
    <h1 class="text-center font-mono text-2xl font-bold italic underline">Admin Panel</h1>

    {#if error || $state.error}
      <div class="alert alert-error">
        <span>Error! {error || $state.error}</span>
      </div>
    {:else if ready}
      {#if hits.length > 0}
        <Admin {hits} {peerjsKey} />
      {:else}
        <div class="alert alert-warning">
          <span>No HITs!</span>
        </div>
      {/if}
    {:else}
      Loading
    {/if}
  </div>
</div>
