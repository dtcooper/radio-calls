<script>
  import { onMount, onDestroy } from "svelte"
  import { state, isPreview } from "../hit"
  import NextButton from "./components/NextButton.svelte"
  import TopicSummary from "./components/CallSummary.svelte"

  export let next

  let highlight = false
  let highlightTimeout

  onMount(() => {
    if (!isPreview) {
      setTimeout(() => (highlight = true), 5000)
    }
  })

  onDestroy(() => clearTimeout(highlightTimeout))
</script>

<p>
  This is will be a <strong>funny</strong> and <strong>enjoyable</strong> assignment 😂😂😂 where you'll use your web
  browser to call 📞 people on a <em>live</em> radio show / podcast. 📻
</p>

<p>The goal is to have a conversation and talk to the host(s) of the radio show about the following topic,</p>

<TopicSummary overviewOnly={true} />

<p>
  💰🤑💰
  <strong>
    <span class="text-success">$$$</span>
    Bonuses will be awarded to longer, weirder, or funnier calls!
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
  to <strong>leave a voice mail</strong> 📬 and submit the assignment.
</p>

<p>
  Once connected, you will have to stay on the call for <em>at least</em>
  <strong>{$state.minCallDuration.humanize()}</strong>, but you are more than welcome to talk as long as you would like!
</p>

<NextButton {next} {highlight} disabled={isPreview}>
  {#if isPreview}
    You are currently previewing this assignment.
    <span class="hidden sm:contents">Press ACCEPT to start.</span>
  {:else}
    Continue with assignment
  {/if}
</NextButton>
