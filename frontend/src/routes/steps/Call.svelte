<script>
  import NextButton from "./components/NextButton.svelte"
  import TopicSummary from "./components/CallSummary.svelte"
  import Notice from "./components/Notice.svelte"
  import { slide } from "svelte/transition"
  import { state, debugMode, scroll } from "../hit"
  import { CALL_STEP_CALL, CALL_STEP_VOICEMAIL } from "$lib/shared-constants.json"

  export let next

  $: callDisabled = $state.callInProgress || $state.done

  let scrolledOnDone = false // $state is a little too reactive, so protect scrolling more than once
  $: if ($state.done && !scrolledOnDone) {
    if ($debugMode) {
      console.log("Call state moved to done!")
    }
    scroll("next-btn")
    scrolledOnDone = true
  }

  const submit = () => {
    state.logProgress("call done")
    state.hangup()
    next()
  }
</script>

<p>Now it's time to make your call! 😆😆😆 <em class="text-accent">Have fun!</em></p>

<p>
  When you're ready, press the call button below to start. Make sure you have a working microphone and headset
  beforehand. We'll be testing it first.
</p>

{#if $state.callInProgress && $state.wordsHeard}
  <div transition:slide>
    <Notice type="error">
      {#if $state.wordsHeard === "<<<SILENCE>>>"}
        <em class="font-bold">We heard nothing!</em> Are you sure that you have a working microphone with the level turned
        up? 🎤️🎙️️🎤️
      {:else}
        We heard the following: <em>"{$state.wordsHeard}"</em> &mdash; which is incorrect. We're expecting
        <strong>{$state.numWordsToPronounce} words</strong>, and
        <strong>all of them are fruits</strong>. Please listen and try again!
      {/if}
    </Notice>
  </div>
{/if}
{#if [CALL_STEP_CALL, CALL_STEP_VOICEMAIL].includes($state.callStep)}
  <div transition:slide>
    <Notice type="info">
      <p>
        <strong>IMPORTANT:</strong>
        <em>
          A <strong>silent {$state.callStep === CALL_STEP_VOICEMAIL ? "voicemail" : "call"}</strong>
          where you do not speak will result in a <strong class="underline">REJECTED</strong> assignment!
        </em>
      </p>
      <p>
        As long as you <strong>speak</strong> 🗣 and <strong>discuss the topic</strong>, your assignment will be
        <strong class="underline">APPROVED!</strong> 😁✅😁
      </p>
    </Notice>
  </div>
{/if}

<TopicSummary />

<p>
  <span class="hidden text-success lg:contents">💰🤑💰</span>
  <strong>
    <span class="hidden text-success lg:inline">$$$</span>
    Bonuses may be awarded to longer, weirder, or funnier calls!
    <span class="text-success">$$$</span>
  </strong>
  💰🤑💰
</p>

<div class="mt-2 flex flex-col justify-center gap-2 sm:flex-row md:mt-3 md:gap-5">
  <button
    class="btn btn-info btn-sm sm:btn-md md:btn-lg md:!text-2xl"
    disabled={callDisabled}
    on:click={() => state.call()}
    class:animate-highlight-shadow={!callDisabled}
    class:shadow-info={!callDisabled}
  >
    📞 Click to start call 📞
  </button>
  {#if $debugMode && $state.isStaff && !$state.isProd}
    <button
      class="btn btn-secondary btn-sm sm:btn-md md:btn-lg md:!text-2xl"
      disabled={callDisabled}
      on:click={() => state.call(true)}
    >
      Cheat!
    </button>
  {/if}
  <button
    class="btn btn-warning btn-sm sm:btn-md md:btn-lg md:!text-2xl"
    disabled={!$state.canHangUp}
    on:click={() => state.hangup()}
  >
    {#if $state.callStep === CALL_STEP_VOICEMAIL}
      📬 Finish voicemail 📬
    {:else}
      🚫 Hang up 🚫
    {/if}
  </button>
</div>

<NextButton next={submit} disabled={!$state.done} />
