<script>
  export let term = 0
  export let index = 0

  $: accepted = term > index
  $: enabled = term === index

  const accept = () => {
    if (!accepted) {
      term += 1
    }
  }
</script>

<div class="flex items-center justify-center">
  <input
    type="checkbox"
    class="checkbox checkbox-sm sm:checkbox-md md:checkbox-lg"
    class:pointer-events-none={!enabled}
    class:checkbox-error={enabled}
    class:checkbox-info={accepted}
    disabled={!enabled && !accepted}
    on:click={accept}
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
  class:pointer-events-none={!enabled}
  on:click={accept}
>
  <slot />
</div>
