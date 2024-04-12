<script>
  export let next
  export let disabled = false
  export let highlight = true
  let classes = "btn-accent"
  export { classes as class }
</script>

<p class="my-1 mt-2 flex flex-col justify-center text-center sm:mt-3 sm:flex-row md:mt-4">
  <button
    id="next-btn"
    style="--highlight-color: oklch(var(--btn-color))"
    class="btn btn-sm sm:btn-md md:btn-lg md:!text-2xl {classes}"
    class:animate-highlight-shadow={highlight && !disabled}
    {disabled}
    on:click={() => next()}
  >
    <slot>Continue with assignment 💘</slot>
  </button>
</p>
