<script>
  export let next
  export let disabled = false
  export let highlight = true
  let classes = "btn-success"
  export { classes as class }
</script>

<p class="mt-2 text-center sm:mt-3 md:mt-4">
  <button
    style="--highlight-color: oklch(var(--btn-color))"
    class="btn btn-xs sm:btn-sm md:btn-lg {classes}"
    class:animate-highlight-shadow={highlight && !disabled}
    {disabled}
    on:click={() => next()}
  >
    <slot>Continue with assignment</slot>
  </button>
</p>
