<script>
  import TOSTerm from "./components/TOSTerm.svelte"
  import { state, isDebug } from "../hit"

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

<blockquote class="ml-5 flex flex-col gap-3 border-l-2 border-base-300 pl-2">
  <div><strong>Carefully</strong> read each term &amp; condition below, then click to agree.</div>
  <span class="text-error">
    If you <strong>disagree</strong> with <em>any</em> of these terms,
    <em><strong><u>DO NOT</u> continue with this assignment!</strong></em>
  </span>
</blockquote>

<div class="grid grid-cols-[max-content_auto] items-center gap-x-3 gap-y-2">
  <div class="flex flex-col items-center font-mono italic">
    <span class="text-xs font-bold underline sm:text-sm">I agree!</span>
    <em class="hidden text-xs sm:inline">(click to accept)</em>
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
      Your call will be <u>recorded</u> and <u>broadcast</u> on a radio show 📻 (and associated podcast).
    </strong>
  </TOSTerm>
  <TOSTerm bind:term index={nextIndex()}>
    <span class="text-error"
      >You should <strong><u>NOT</u></strong> mention Amazon Mechanical Turk under <strong><em>any</em></strong> circumstances.</span
    >
  </TOSTerm>
  <TOSTerm bind:term index={nextIndex()}>
    Have any conversation you'd like, but the call should be placed to discuss the topic: <em class="text-secondary"
      >{$state.topic}</em
    >
  </TOSTerm>
  <TOSTerm bind:term index={nextIndex()}>
    If no one answers, you will be placed on a hold loop. You understand, that...

    <ul class="mt-2 list-disc">
      <li class="ml-5">You <strong><u>CANNOT</u></strong> submit the assignment without completing the call;</li>
      <li class="ml-5">There is a chance the host may not answer the call;</li>
      <li class="ml-5">
        The assignment may take a very long time if you end up waiting for the host to answer your call; and
      </li>
      <li class="ml-5">
        If the host does not answer your call, you'll have to return the HIT &mdash; but this won't affect your rating.
      </li>
    </ul>
  </TOSTerm>
</div>

<p class="text-center">
  <button class="btn btn-warning btn-xs sm:btn-sm md:btn-lg" on:click={next} disabled={numTerms !== term && !isDebug}>
    I have carefully read, understand &amp; agree to the above terms.
  </button>
</p>
