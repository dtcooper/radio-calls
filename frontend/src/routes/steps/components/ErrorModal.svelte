<script>
  import { state } from "../../hit"

  const dismiss = () => state.setFailure("")
</script>

<dialog class="modal" class:modal-open={$state.failure}>
  <div class="modal-box bg-error text-error-content">
    <form method="dialog">
      <button class="btn btn-circle btn-ghost btn-sm absolute right-2 top-2" on:click={dismiss}>✕</button>
    </form>
    <h3 class="text-lg font-bold sm:text-xl md:text-2xl">An Error Occurred</h3>
    <p class="py-4 text-base sm:text-lg">{$state.failure}</p>
    <div class="modal-action">
      <form method="dialog">
        <button class="btn md:btn-lg" on:click={dismiss}>Dismiss</button>
      </form>
    </div>
  </div>
</dialog>
