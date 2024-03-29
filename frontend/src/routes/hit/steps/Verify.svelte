<script>
  import { state, debugMode } from "../hit"
  import { slide } from "svelte/transition"

  export let next

  let playing = false
  let playedOnce = false
  const play = async () => {
    playing = playedOnce = true
    await state.playPronouncer()
    playing = false
  }

  let recording = false
  let success = false
  let abort = null
  let failedHeardWords = null

  const record = async () => {
    failedHeardWords = null
    recording = true
    const { abort: _abort, promise } = state.recordWords()
    abort = _abort

    const { success: _success, heardWords } = await promise
    if (_success) {
      success = true
    } else {
      failedHeardWords = heardWords
    }

    abort = null
    recording = false
  }

  const submit = () => {
    if (abort) {
      abort.abort()
      abort = null
    }
  }

  $: playDisabled = playing || recording
  $: recordDisabled = (!playedOnce && !$debugMode) || playing || recording
  $: submitDisabled = !abort
</script>

<p>
  Now we'll verify whether you can <strong>speak</strong> and <strong>understand English</strong>.<br />
  We'll confirm you have a <strong>working microphone</strong> 🎙 and <strong>speaker</strong> 🔊.
</p>

<hr class="h-px border-neutral" />
<h3 class="ml-10 font-mono text-xl font-bold italic text-accent md:text-2xl">Step 1: Play Phrase</h3>

<p>
  Press the button below to play {$state.pronouncer.length}-word phrase containing the <strong>names of fruits</strong>.
  🍓🍇🍌
  <br />You'll have to repeat them in the next step, so <strong><em>listen carefully!</em></strong>
</p>

<p class="mb-3 text-center">
  <button class="btn btn-primary btn-xs sm:btn-sm md:btn-lg" on:click={play} disabled={playDisabled}>
    📕 Click here to play words 📕
  </button>
</p>

<hr class="h-px border-neutral" />
<h3 class="ml-10 font-mono text-xl font-bold italic text-accent md:text-2xl">Step 2: Repeat Phrase</h3>

<p>
  Now it's time to repeat the {$state.pronouncer.length}-word phrase you heard in Step 1.<br />
  If you need to hear them again &mdash;
  <button class="btn btn-primary btn-xs" on:click={play} disabled={!playedOnce || playDisabled}>click here!</button>
</p>

<p>
  Press the button below and start recording yourself saying the {$state.pronouncer.length} phrase &mdash;
  <em>remember: they're all fruits!</em><br />
  When you are done, press submit.
</p>

{#if failedHeardWords}
  <div class="alert alert-warning" transition:slide>
    <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 shrink-0 stroke-current" fill="none" viewBox="0 0 24 24"
      ><path
        stroke-linecap="round"
        stroke-linejoin="round"
        stroke-width="2"
        d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
      /></svg
    >
    <span>
      {#if failedHeardWords.length}
        We heard the following incorrect phrase: <em class="capitalize">"{failedHeardWords.join(", ")}".</em> Please try
        again.
      {:else}
        We did not detect any words spoken. Please check your microphone and try again.
      {/if}
    </span>
  </div>
{:else if success}
  <div class="alert alert-success" transition:slide>
    <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 shrink-0 stroke-current" fill="none" viewBox="0 0 24 24"
      ><path
        stroke-linecap="round"
        stroke-linejoin="round"
        stroke-width="2"
        d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
      /></svg
    >
    <span> You repeated the </span>
  </div>
{/if}

<p class="mb-3 flex flex-col items-center justify-center gap-2 sm:flex-row sm:gap-4">
  <button class="btn btn-error btn-xs sm:btn-sm md:btn-lg" on:click={record} disabled={recordDisabled}>
    🗣 Click here to record phrase 🗣
  </button>
  <button class="btn btn-warning btn-xs sm:btn-sm md:btn-lg" on:click={submit} disabled={submitDisabled}>
    Submit phrase
  </button>
</p>
<p></p>
<p>
  {#if $debugMode}
    <code class="badge badge-error gap-2 font-mono capitalize"
      ><strong>DEBUG:</strong> {$state.pronouncer.join(", ")}</code
    >
  {/if}
</p>

<p>
  Troubleshooting: - If you're having trouble, check your microphone levels above. - If you the server has having a hard
  time recognizing your words, this may not be the HIT for you.
</p>

<p><button class="btn btn-success" on:click={next} disabled={!success}>Next</button></p>
