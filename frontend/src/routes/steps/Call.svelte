<script>
  import NextButton from "./components/NextButton.svelte"
  import TopicSummary from "./components/CallSummary.svelte"
  import Warning from "./components/Warning.svelte"
  import { slide } from "svelte/transition"
  import { state, debugMode, STAGE_VOICEMAIL } from "../hit"

  export let next

  $: callDisabled = $state.callInProgress || $state.done

  const submit = () => {
    state.hangup()
    next()
  }
</script>

<p>Now it's time to make your call! 😆😆😆</p>

<p>
  When you're ready, press the call button below to start. Make sure you have a working microphone and headset
  beforehand. We'll be testing it first.
</p>

{#if $state.wordsHeard}
  <div transition:slide>
    <Warning>
      We heard the following words: <em>"{$state.wordsHeard}".</em> Try again.
    </Warning>
  </div>
{/if}

<TopicSummary />

<p>
  <span class="hidden text-success lg:contents">💰🤑💰</span>
  <strong>
    <span class="hidden text-success lg:inline">$$$</span>
    Bonuses will be awarded to longer, weirder, or funnier calls!
    <span class="text-success">$$$</span>
  </strong>
  💰🤑💰
</p>

<div class="mt-2 flex justify-center gap-2 md:mt-3 md:gap-5">
  <button
    class="btn btn-info btn-xs sm:btn-md md:btn-lg md:!text-2xl"
    disabled={callDisabled}
    on:click={() => state.call()}
    class:animate-highlight-shadow={!callDisabled}
    class:shadow-info={!callDisabled}
  >
    📞 Click to start call 📞
  </button>
  {#if $debugMode && $state.isStaff && !$state.isProd}
    <button
      class="btn btn-secondary btn-xs sm:btn-md md:btn-lg md:!text-2xl"
      disabled={callDisabled}
      on:click={() => state.call(true)}
    >
      Cheat!
    </button>
  {/if}
  <button
    class="btn btn-warning btn-xs sm:btn-md md:btn-lg md:!text-2xl"
    disabled={!$state.canHangUp}
    on:click={() => state.hangup()}
  >
    {#if $state.stage === STAGE_VOICEMAIL}
      📬 Finish voicemail 📬
    {:else}
      🚫 Hang up 🚫
    {/if}
  </button>
</div>

<NextButton next={submit} disabled={!$state.done} />
