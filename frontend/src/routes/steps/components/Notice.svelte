<script>
  export let type = "warning"

  let svgPath
  let classes = false
  export { classes as class }
  export let icon = true

  switch (type) {
    case "info":
      classes = classes || "bg-info text-info-content"
      svgPath = "M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
      break
    case "error":
      classes = classes || "bg-error text-error-content"
      svgPath = "M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"
      break
    case "success":
      classes = classes || "bg-success text-success-content"
      svgPath = "M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
      break
    default:
      if (type !== "warning") {
        console.warn(`Invalid notice type: ${type}. Using warning.`)
      }
      classes = classes || "bg-warning text-warning-content"
      svgPath =
        "M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
      break
  }
</script>

<div class="mx-4 my-2 flex items-center gap-2 rounded-lg border-2 border-neutral px-4 py-2 {classes}">
  {#if icon}
    <svg
      xmlns="http://www.w3.org/2000/svg"
      class="size-8 shrink-0 stroke-current sm:size-10 md:size-12"
      fill="none"
      viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d={svgPath} /></svg
    >
  {/if}
  <span class="text-xs sm:text-sm md:text-base lg:text-lg">
    <slot />
  </span>
</div>
