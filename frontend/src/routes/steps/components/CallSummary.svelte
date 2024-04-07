<script>
  import { state } from "../../hit"
  import {
    CALL_STEP_INITIAL,
    CALL_STEP_VERIFIED,
    CALL_STEP_CALL,
    CALL_STEP_VOICEMAIL,
    CALL_STEP_HOLD
  } from "../../../../../backend/shared-constants.json"

  export let overviewOnly = false

  let items

  let callStatus = []
  let countdown = []

  $: countdownDuration = $state.countdownDuration?.format("mm:ss")
  $: if ($state.done) {
    callStatus = ["Assignment completed!", "text-bold text-success"]
    countdown = [false]
  } else if ($state.callInProgress) {
    switch ($state.callStep) {
      case CALL_STEP_INITIAL:
        callStatus = ["Awaiting verification", "text-info animate-pulse"]
        countdown = [false]
        break
      case CALL_STEP_VERIFIED:
        callStatus = ["Connecting...", "text-success animate-pulse"]
        countdown = [false]
        break
      case CALL_STEP_HOLD:
        callStatus = ["On hold", "text-warning animate-pulse"]
        countdown = ["until you can leave a voicemail", "text-info", countdownDuration]
        break
      case CALL_STEP_CALL:
        callStatus = ["On a call", "text-success"]
        countdown = ["until you can hang up", "text-info", countdownDuration]
        break
      case CALL_STEP_VOICEMAIL:
        callStatus = ["Leaving voicemail", "text-error animate-pulse"]
        countdown = [false]
        break
      default:
        callStatus = [`UNKNOWN STATE: ${$state.callStep}`, "text-error"]
        countdown = [false]
    }
  } else {
    callStatus = ["Please start the call", "text-info italic animate-pulse"]
    countdown = [false]
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

<div class="my-0.5 ml-2 sm:my-1 md:mx-6 md:my-1.5 md:ml-4">
  <div
    class="grid grid-cols-[max-content_auto] gap-0.5 border-2 border-base-200 bg-base-200 sm:gap-1 sm:border-4"
    class:md:grid-cols-[max-content_3fr_max-content_2fr]={!overviewOnly}
  >
    {#each items as [name, value, classes, monoPrefix]}
      <div class="flex items-center justify-end bg-base-100 p-2 text-right font-bold">{name}:</div>
      <div class="text-bold flex items-center bg-base-100 p-2 {classes || ''}">
        {#if monoPrefix}
          <span class="contents font-mono">{monoPrefix}</span>
        {/if}
        {value || "-"}
      </div>
    {/each}
  </div>
</div>
