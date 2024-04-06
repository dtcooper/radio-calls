<script>
  export let warning = true
</script>

<div
  class="mx-5 my-2 flex items-center gap-2 rounded-lg px-4 py-2 {warning
    ? 'bg-warning text-warning-content'
    : 'bg-info text-info-content'}"
>
  {#if warning}
    <svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8 shrink-0 stroke-current" fill="none" viewBox="0 0 24 24"
      ><path
        stroke-linecap="round"
        stroke-linejoin="round"
        stroke-width="2"
        d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
      /></svg
    >
  {:else}
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" class="h-8 w-8 shrink-0 stroke-current"
      ><path
        stroke-linecap="round"
        stroke-linejoin="round"
        stroke-width="2"
        d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
      ></path></svg
    >
  {/if}
  <span class="text-xs sm:text-sm md:text-base lg:text-lg">
    <slot />
  </span>
</div>
