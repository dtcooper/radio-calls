<script>
  import dayjs from "dayjs"
  import { onMount, onDestroy } from "svelte"
  import { state, STAGE_INITIAL, STAGE_VERIFIED, STAGE_CALL, STAGE_VOICEMAIL, STAGE_HOLD, STAGE_DONE } from "../../hit"

  export let overviewOnly = false

  let items

  let interval
  let now = dayjs()

  let callStatus = []
  let countdown = []

  onMount(() => {
    if (!overviewOnly) {
      interval = setInterval(() => (now = dayjs()), 500)
    }
  })
  onDestroy(() => {
    if (!overviewOnly) {
      clearInterval(interval)
    }
  })

  $: countdownDuration = $state.countdownDuration?.format("mm:ss")
  $: if ($state.done) {
    callStatus = ["Assignment completed!", "text-bold text-success"]
    countdown = ["-"]
  } else if ($state.callInProgress) {
    switch ($state.stage) {
      case STAGE_INITIAL:
        callStatus = ["Awaiting verification", "text-info animate-pulse"]
        countdown = ["-"]
        break
      case STAGE_VERIFIED:
        callStatus = ["Verified! Connecting.", "text-success animate-pulse"]
        countdown = ["-"]
        break
      case STAGE_HOLD:
        callStatus = ["On hold", "text-warning animate-pulse"]
        countdown = [`${countdownDuration} until you can leave a voicemail`, "text-info"]
        break
      case STAGE_CALL:
        callStatus = ["On a call", "text-success"]
        countdown = [`${countdownDuration} until you can hang up`, "text-info"]
        break
      case STAGE_VOICEMAIL:
        callStatus = ["Leaving voicemail", "text-error animate-pulse"]
        countdown = ["-"]
        break
      default:
        callStatus = [`UNKNOWN STATE: ${$state.stage}`, "text-error"]
        countdown = ["-"]
    }
  } else {
    callStatus = ["Please start the call", "text-info italic animate-pulse"]
    countdown = ["-"]
  }

  $: {
    // Be reactive if anything in $state changes
    items = []

    items.push(
      ["Show topic", $state.topic, `text-secondary ${overviewOnly ? "" : "md:col-span-3 text-primary"}`],
      ["Show host(s)", $state.showHost]
    )
    if (!overviewOnly) {
      items.push(["Call status", ...callStatus], ["Countdown", ...countdown], ["Your name", `${$state.name}`])
    }
  }
</script>

<div class="ml-2 md:mx-6 md:ml-4">
  <div
    class="inline-grid grid-cols-[max-content_auto] gap-0.5 border-2 border-base-200 bg-base-200 sm:gap-1 sm:border-4 md:grid"
    class:md:grid-cols-[max-content_3fr_max-content_2fr]={!overviewOnly}
  >
    {#each items as [name, value, classes]}
      <div class="flex items-center justify-end bg-base-100 p-2 text-right font-bold">{name}:</div>
      <div class="text-bold flex items-center bg-base-100 p-2 {classes || ''}">{value}</div>
    {/each}
  </div>
</div>
