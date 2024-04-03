<script>
  import { state, isPreview } from "../hit"

  export let next
</script>

<p>
  This is will be a <strong>funny</strong> and <strong>enjoyable</strong> assignment 😂😂😂 where you'll use your web
  browser to call 📞 people on a <em>live</em> radio show / podcast. 📻
</p>

<p>The goal is to have a conversation and talk to the host(s) of the radio show.</p>

<div class="ml-4 grid grid-cols-[max-content_1fr] gap-2 border-l-4 border-base-300 pl-2">
  <div class="text-right">Conversation topic:</div>
  <div class="font-bold text-primary">{$state.topic}</div>
  <blockquote class="text-right">Show Host(s):</blockquote>
  <div class="font-bold text-primary">{$state.showHost}</div>
</div>

<p>
  💰🤑💰
  <strong>
    <span class="text-success">$$$</span>
    Bonuses will be awarded to longer, stranger, or funnier calls!
    <span class="text-success">$$$</span>
  </strong>
  💰🤑💰
</p>

<p>Note: the host(s) of the program will be expecting your call.</p>

<p>
  <small
    >TODO: IMPLEMENT min_call_time AND leave_voicemail_after_time (5 mins should add some constant to min_call_time to
    account for the verify step)</small
  ><br />

  This assignment will take approximately 5 to 15 minutes to complete. 🕒🕒🕒<br />
  If after 15 minutes you are still not connected to the host, you'll have the opportunity to
  <strong>leave a voice mail</strong> 📬 and submit the assignment.
</p>

<p>
  Once connected, you will have to stay on the call for <em>at least 2 minutes</em>, but you are more than welcome to
  talk as long as you would like!
</p>

<p class="text-center">
  <button class="btn btn-success btn-xs sm:btn-sm md:btn-lg" disabled={isPreview} on:click={next}>
    {#if isPreview}
      You are currently previewing this assignment.
      <span class="hidden sm:contents">Press ACCEPT to start.</span>
    {:else}
      Continue with assignment
    {/if}
  </button>
</p>
