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

<div id="tos-term-{index}" class="flex items-center justify-center">
  <input
    type="checkbox"
    class="checkbox checkbox-sm shadow-error sm:checkbox-md md:checkbox-lg"
    class:pointer-events-none={!enabled}
    class:checkbox-error={enabled}
    class:checkbox-info={accepted}
    class:animate-highlight-shadow={enabled}
    disabled={!enabled && !accepted}
    on:click={accept}
    bind:checked={accepted}
  />
</div>
<!-- svelte-ignore a11y-click-events-have-key-events -->
<!-- svelte-ignore a11y-no-static-element-interactions -->
<div
  class="rounded-xl border-2 px-2 py-1 sm:text-base md:text-lg {enabled
    ? 'cursor-pointer border-error'
    : 'pointer-events-none border-transparent'}"
  on:click={accept}
>
  <slot />
</div>
