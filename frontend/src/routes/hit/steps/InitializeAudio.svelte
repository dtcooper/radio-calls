<script>
  import { state, debugMode } from "../hit"

  export let next
  let btnDisabled = false
  let badgeClass = "badge-warning"
  let badgeText = "Click button enable microphone..."
  let tooltip = null

  const enableMic = async () => {
    btnDisabled = true
    const { message } = await state.initializeAudio()
    badgeText = message
    if ($state.audioInitialized) {
      badgeClass = "badge-success"
      if ($debugMode) {
        next()
      }
    } else {
      badgeClass = "badge-error"
      btnDisabled = false
      tooltip = "Fix your mic and try again!"
    }
  }
</script>

<p>Now it's time to enable your audio.</p>

<p>Click the button below to authorize the use of your microphone 🎙</p>

<div class="flex items-center gap-2">
  Microphone status: <div class="badge badge-sm sm:badge-md md:badge-lg {badgeClass}">{badgeText}</div>
</div>

<p class="text-center">
  <button
    class="btn btn-primary btn-xs tooltip-bottom tooltip-warning sm:btn-sm md:btn-lg"
    class:tooltip
    data-tip={tooltip && !$state.audioInitialized ? tooltip : ""}
    on:click={enableMic}
    disabled={btnDisabled || $state.audioInitialized}
  >
    🎙 Click here to enable microphone 🎙
  </button>
</p>

<p class="text-center">
  <button class="btn btn-success btn-xs sm:btn-sm md:btn-lg" on:click={next} disabled={!$state.audioInitialized}>
    Continue with assignment
  </button>
</p>
