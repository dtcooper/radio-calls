<script>
  import { state, isPreview } from "../hit"

  export let next
</script>

<p>
  This is will be a <strong>funny</strong> and <strong>enjoyable</strong> Assignment 😂😂😂 where you'll use your web
  browser to call 📞 people on a <em>live</em> radio show. 📻
</p>

<p>You will talk to the host(s) of the radio show about the following topic....</p>

<blockquote class="ml-5 border-l-2 border-base-300 pl-2 font-mono font-bold italic text-secondary">
  {$state.topic}
</blockquote>

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

<p>This assignment will take approximately 5 to 10 minutes to complete. 🕒🕒🕒</p>

<p>
  You will have to stay on the call for <em>at least 2 minutes</em>, but you are welcome to talk as long as you would
  like!
</p>

<p class="text-center">
  <button class="btn btn-success btn-xs sm:btn-sm md:btn-lg" disabled={isPreview} on:click={next}>
    {#if isPreview}
      You are currently <em class="underline">previewing</em> this assignment. Press ACCEPT to start.
    {:else}
      Continue with assignment
    {/if}
  </button>
</p>
