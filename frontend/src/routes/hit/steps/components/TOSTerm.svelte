<script>
  export let term = 0
  export let index = 0

  $: accepted = term > index
  $: enabled = term === index
</script>

<div class="flex items-center justify-center">
  <input
    type="checkbox"
    class="checkbox-error checkbox checkbox-sm sm:checkbox-md md:checkbox-lg"
    class:pointer-events-none={accepted}
    disabled={!enabled && !accepted}
    on:click={() => {
      if (!accepted) {
        term += 1
      }
    }}
    bind:checked={accepted}
  />
</div>
<!-- svelte-ignore a11y-click-events-have-key-events -->
<!-- svelte-ignore a11y-no-static-element-interactions -->
<div
  class="rounded-xl border-2 px-2 py-1 sm:px-3 sm:text-base md:text-lg"
  class:cursor-pointer={enabled}
  class:border-error={enabled}
  class:border-base-100={!enabled}
  on:click={() => {
    if (!accepted) {
      term += 1
    }
  }}
>
  <slot />
</div>
