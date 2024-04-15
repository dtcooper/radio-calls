<script>
  import { onMount, onDestroy } from "svelte"
  import { state, isPreview } from "../hit"
  import Notice from "./components/Notice.svelte"
  import NextButton from "./components/NextButton.svelte"
  import TopicSummary from "./components/CallSummary.svelte"

  export let next

  let highlight = false
  let highlightTimeout

  onMount(() => {
    if (!isPreview) {
      setTimeout(() => (highlight = true), 4000)
    }
  })

  onDestroy(() => clearTimeout(highlightTimeout))
</script>

<p>
  This is a <strong>funny</strong> and <strong>enjoyable</strong> assignment 😂😂😂 where you'll use your web browser to
  call 📞 a <em>live</em> radio show / podcast. 📻
</p>

<Notice
  type="info"
  class="animate-highlight-shadow bg-warning text-warning-content shadow-warning"
  --highlight-amount="9px"
>
  <p>It has come to our attention that <strong>our requester approval rating is low</strong>. 😭</p>
  <p>
    This is due to our <em>higher paying HITs</em> and a <strong class="italic">large amount of spam</strong> on Mechanical
    Turk. 🚮
  </p>
  <p>
    Rest assured, if you <strong>complete the assignment correctly,</strong>
    <em>you <span class="underline">will be <strong>approved</strong></span>!</em> 😁✅😁
  </p>
</Notice>

<p>The goal is to have a conversation and talk to the host(s) of the radio show about the following topic,</p>

<TopicSummary overviewOnly={true} />

<p>
  💰🤑💰
  <strong>
    <span class="text-success">$$$</span>
    Bonuses may be awarded to longer, weirder, or funnier calls!
    <span class="text-success">$$$</span>
  </strong>
  💰🤑💰
</p>

<p><strong>NOTE:</strong> the host(s) of the program will be expecting your call.</p>

<p>
  This assignment will take approximately
  {$state.estimatedBeforeVerifiedDuration.add($state.minCallDuration).humanize()} to
  {$state.leaveVoicemailAfterDuration.humanize()} to complete. 🕒🕒🕒<br />
  If after {$state.leaveVoicemailAfterDuration.humanize()} you are still not connected to the host, you'll have the opportunity
  to <strong>leave a voice mail</strong> 📬 and submit the assignment <em>anyway.</em>
</p>

<p>
  Once connected, you <strong>must</strong> stay on the call for <em>at least</em>
  <strong>{$state.minCallDuration.humanize()}</strong>. Of course, you're more than welcome to talk as long as you would
  like! 👍
</p>

<NextButton {next} {highlight} disabled={isPreview}>
  {#if isPreview}
    You're previewing this assignment.
    <span class="hidden sm:contents">Press ACCEPT to start.</span>
  {:else}
    Okay! I'm ready to begin! 💘
  {/if}
</NextButton>
