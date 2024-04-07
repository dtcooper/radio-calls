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

  $: if (term > 0) {
    document.getElementById(`tos-term-${term}`)?.scrollIntoView({ behavior: "smooth", block: "center" })
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

  <TOSTerm bind:term index={nextIndex()} {numTerms}>
    <strong>You <u>MUST</u> speak in English.</strong>
  </TOSTerm>
  <TOSTerm bind:term index={nextIndex()} {numTerms}>
    You <u>MUST</u> have a <em>working</em> headset 🎧 (or speaker 🔉) with a <u>microphone</u>. 🎤️🎙️️
  </TOSTerm>
  <TOSTerm bind:term index={nextIndex()} {numTerms}>
    <strong>
      Your call will be <u>recorded</u> and <u>broadcast</u> on a radio show 📻 (or podcast).
    </strong>
  </TOSTerm>
  <TOSTerm bind:term index={nextIndex()} {numTerms}>
    <span class="text-error">
      You should <strong><u>NOT</u></strong> mention Amazon Mechanical Turk under <strong><em>any</em></strong> circumstances.
    </span>
    <br />Pretend you're a <strong class="text-success">real caller</strong> of the show.
  </TOSTerm>
  <TOSTerm bind:term index={nextIndex()} {numTerms}>
    <p>You have good internet connectivity, since it will be needed to complete this assignment. 🌎💻🔌</p>
    <p>
      <strong class="text-error">Getting disconnected will prevent you from submitting the assignment!</strong>
      😩😩😩
    </p>
  </TOSTerm>
  <TOSTerm bind:term index={nextIndex()} {numTerms}>
    <div>
      <p>You may have any conversation you'd like, but you should discuss the following,</p>
      <div class="ml-1 mt-1 border-l-2 border-base-300 pl-3">
        Topic: <em class="font-bold text-secondary">{$state.topic}</em>
      </div>
    </div>
  </TOSTerm>
  <TOSTerm bind:term index={nextIndex()} {numTerms}>
    You may discuss adult subject matter &ndash; sex, drugs, etc &ndash; or <em>even insult the host(s)</em> 🤣, but:
    <br class="hidden lg:inline" />
    <strong class="underline">Please refrain from swearing or cursing!</strong> 🔞🤬🍆
  </TOSTerm>
  <TOSTerm bind:term index={nextIndex()} {numTerms}>
    <strong>If no one answers, you will be placed on <span class="text-primary">a hold loop.</span> 🔁</strong>
    If that happens, <strong class="italic text-success">DON'T PANIC!</strong><br />
    You understand, that...

    <ul class="mt-2 list-disc">
      <li class="ml-5">
        You <strong><u>CANNOT</u></strong> submit the assignment without completing the call or leaving a voicemail;
      </li>
      <li class="ml-5">
        There is a chance the host may not answer the call, and <strong class="text-primary"
          >that means you'll be placed on hold</strong
        >;
      </li>
      <li class="ml-5">
        The assignment <strong class="text-error underline"
          >may take up to {$state.leaveVoicemailAfterDuration.humanize()} or more</strong
        >, especially if you end up on hold, waiting for the host to answer your call; and
      </li>
      <li class="ml-5">
        If the host does not answer your call,
        <strong class="text-primary"
          >after holding for {$state.leaveVoicemailAfterDuration.humanize()} you may leave a voicemail 📬</strong
        >
        and submit the assignment; <strong class="italic underline">OR</strong> you can always return the HIT &mdash; this
        won't affect your rating.
      </li>
      <li class="ml-5">
        This means you'll <em class="font-bold text-success">
          be able to submit the assignment after, even if you are placed on hold!</em
        >
        😁
      </li>
    </ul>
  </TOSTerm>
  <TOSTerm bind:term index={nextIndex()} {numTerms}>
    <p class="text-base text-error md:text-xl lg:gap-3 lg:text-2xl">
      <strong>IMPORTANT:</strong>
      <em
        >A <strong>silent call</strong> or <strong>silent voicemail</strong> where you do not speak will result in a
        <strong class="underline">REJECTED</strong> assignment!</em
      >
    </p>
  </TOSTerm>
</div>

<NextButton {next} disabled={numTerms !== term && !$debugMode} class="btn-warning" highlight={numTerms === term}>
  I have
  <span class="contents sm:hidden">read</span>
  <span class="hidden sm:contents">carefully read, understand</span>
  &amp; agree to the above terms.
</NextButton>
