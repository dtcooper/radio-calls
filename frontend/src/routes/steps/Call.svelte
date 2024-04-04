<script>
  import NextButton from "./components/NextButton.svelte"
  import TopicSummary from "./components/CallSummary.svelte"
  import { state, debugMode, STAGE_VOICEMAIL } from "../hit"

  export let next

  $: callDisabled = $state.callInProgress || $state.done

  const submit = () => {
    state.hangup()
    next()
  }
</script>

<p>Now it's time to make your call! 😆😆😆</p>

<p>Press the call button below to start. Make sure you have a working microphone and headset.</p>

<TopicSummary />

<div class="mt-2 flex justify-center gap-2 md:mt-3 md:gap-5">
  <button
    class="btn btn-info md:btn-lg md:!text-2xl"
    disabled={callDisabled}
    on:click={() => state.call()}
    class:animate-highlight-shadow={!callDisabled}
    class:shadow-info={!callDisabled}
  >
    📞 Click to start call 📞
  </button>
  {#if $debugMode && $state.isStaff}
    <button class="btn btn-secondary md:btn-lg md:!text-2xl" disabled={callDisabled} on:click={() => state.call(true)}>
      Cheat!
    </button>
  {/if}
  <button class="btn btn-warning md:btn-lg md:!text-2xl" disabled={!$state.canHangUp} on:click={() => state.hangup()}>
    {#if $state.stage === STAGE_VOICEMAIL}
      📬 Finish voicemail 📬
    {:else}
      🚫 Hang up 🚫
    {/if}
  </button>
</div>

<NextButton next={submit} disabled={!$state.done} />
