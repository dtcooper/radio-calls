<script>
  import TOSTerm from "./components/TOSTerm.svelte"
  import NextButton from "./components/NextButton.svelte"
  import { state, debugMode } from "../hit"

  export let next
  let term = 0
  let numTerms = 0

  const nextIndex = () => {
    numTerms = numTerms + 1
    return numTerms - 1
  }

  $$restProps // Ignore unused
</script>

<h2 class="text-center text-lg sm:text-xl md:text-3xl">
  <span class="font-mono font-bold italic">Important Terms &amp; Conditions</span>
  ⚖️⚖️⚖️
</h2>

<blockquote class="ml-5 flex flex-col gap-3 border-l-2 border-base-300 py-1 pl-2 md:py-2">
  <div><strong>Carefully</strong> read each term &amp; condition below, then click to agree.</div>
  <span class="text-error">
    If you <strong>disagree</strong> with <em>any</em> of these terms,
    <em><strong><u>DO NOT</u> continue with this assignment!</strong></em>
  </span>
</blockquote>

<div class="grid grid-cols-[max-content_auto] items-center gap-x-3 gap-y-2">
  <div class="flex flex-col items-center font-mono italic">
    <div class="text-xs font-bold underline sm:text-sm">I agree!</div>
    <div class="hidden text-xs italic sm:inline">(click to accept)</div>
  </div>
  <div class="text-center font-mono font-bold italic underline">Term</div>

  <TOSTerm bind:term index={nextIndex()}>
    <strong>You <u>MUST</u> speak in English.</strong>
  </TOSTerm>
  <TOSTerm bind:term index={nextIndex()}>
    You <u>MUST</u> have a <em>working</em> headset 🎧 (or speaker 🔉) with a <u>microphone</u>. 🎤️🎙️️
  </TOSTerm>
  <TOSTerm bind:term index={nextIndex()}>
    <strong>
      Your call will be <u>recorded</u> and <u>broadcast</u> on a radio show 📻 (or podcast).
    </strong>
  </TOSTerm>
  <TOSTerm bind:term index={nextIndex()}>
    <span class="text-error"
      >You should <strong><u>NOT</u></strong> mention Amazon Mechanical Turk under <strong><em>any</em></strong> circumstances.</span
    >
  </TOSTerm>
  <TOSTerm bind:term index={nextIndex()}>
    <div>
      <p>You may have any conversation you'd like, but you should discuss the topic:</p>
      <div class="ml-1 mt-1 border-l-2 border-base-300 pl-3">
        Topic: <em class="font-bold text-secondary">{$state.topic}</em>
      </div>
    </div>
  </TOSTerm>
  <TOSTerm bind:term index={nextIndex()}>
    You may discuss adult subject matter (sex, drugs, etc...), or <em>even insult the hosts</em> 🤣, but:
    <br class="hidden lg:inline" />
    <strong class="underline">Please refrain from swearing or cursing!</strong> 🔞🤬🍆
  </TOSTerm>
  <TOSTerm bind:term index={nextIndex()}>
    If no one answers, you will be placed on a hold loop. You understand, that...

    <ul class="mt-2 list-disc">
      <li class="ml-5">
        You <strong><u>CANNOT</u></strong> submit the assignment without completing the call or leaving a voicemail;
      </li>
      <li class="ml-5">There is a chance the host may not answer the call;</li>
      <li class="ml-5">
        The assignment <strong class="underline"
          >may take up to {$state.leaveVoicemailAfterDuration.humanize()} or more</strong
        >
        if you end up needing to wait for the host to answer your call; and
      </li>
      <li class="ml-5">
        If the host does not answer your call, you have the option of leaving a voicemail 📬 and submitting; <strong
          >OR</strong
        > you can always return the HIT &mdash; this won't affect your rating.
      </li>
    </ul>
  </TOSTerm>
  <TOSTerm bind:term index={nextIndex()}>
    <p>You have good internet connectivity, since it will be needed to complete this assignment. 🌎💻🔌</p>
    <p>
      <strong class="text-error">Getting disconnected is a sure-fire way to be unable to submit this assignment!</strong
      >
      😩😩😩
    </p>
  </TOSTerm>
  <TOSTerm bind:term index={nextIndex()}>
    <span class="hidden text-success lg:contents">💰🤑💰</span>
    <strong>
      <span class="hidden text-success lg:inline">$$$</span>
      Bonuses will be awarded to longer, weirder, or funnier calls!
      <span class="text-success">$$$</span>
    </strong>
    💰🤑💰
  </TOSTerm>
</div>

<NextButton {next} disabled={numTerms !== term && !$debugMode} class="btn-warning" highlight={numTerms === term}>
  I have
  <span class="contents sm:hidden">read</span>
  <span class="hidden sm:contents">carefully read, understand,</span>
  &amp; agree to the above terms.
</NextButton>
