<script>
  import { state } from "../hit"

  /** @type {() => void} */
  export let next
  let btnDisabled = false
  let badgeClass = "badge-info"
  let badgeText = "Click button enable microphone..."

  const enableMic = async () => {
    btnDisabled = true
    const { success, message } = await state.enableMic()
    badgeText = message
    if (success) {
      badgeClass = "badge-success"
    } else {
      badgeClass = "badge-warning"
      btnDisabled = false
    }
  }
</script>

<div class="flex flex-col gap-4">
  <p class="text-xl">
    Now it's time to enable your microphone. We'll ensure you have a working microphone to complete this assignment.
  </p>
  <div class="flex items-center gap-2 text-lg">
    Status: <div class="badge badge-lg {badgeClass}">{badgeText}</div>
  </div>
  <p class="text-center">
    <button class="btn btn-primary btn-xs sm:btn-sm md:btn-lg" on:click={enableMic} disabled={btnDisabled}>
      🎙 Click here to enable microphone 🎙
    </button>
  </p>
  <p class="text-center">
    <button class="btn btn-success btn-xs sm:btn-sm md:btn-lg" on:click={next} disabled={!$state.stream}>
      Continue with assignment
    </button>
  </p>
</div>
