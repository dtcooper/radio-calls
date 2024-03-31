<script>
  import { state } from "../admin"
</script>

<div class="flex flex-col gap-3">
  <h2 class="text-center text-xl leading-none">
    Topic: <strong>{$state.hit.topic}</strong><br />
    <span class="text-xs">[{$state.hit.peerId}]</span>
  </h2>

  <div class="grid grid-cols-[auto_1fr_auto_1fr] items-center gap-3 px-2">
    <div>Microphone 🎙</div>
    <div class="mr-4">
      <progress class="progress progress-error h-3" value={$state.micLevel} max="100"></progress>
    </div>
    <div class="ml-4">Speaker 🔊</div>
    <div>
      <progress class="progress progress-success h-3" value={$state.speakerLevel} max="100"></progress>
    </div>
  </div>
  <hr class="h-px border-neutral" />

  <div class="grid grid-cols-[min-content_1fr_1fr_1fr_min-content] items-baseline gap-2">
    {#each ["#", "Assignment ID", "Caller Name", "Peer ID", "action"] as colName}
      <div class="rounded-lg bg-neutral px-3 py-1 text-center text-sm font-bold italic text-neutral-content">
        {colName}
      </div>
    {/each}
    <div class="col-span-5 text-center text-xl italic">No calls at this time!</div>
  </div>
</div>

{#each Object.values($state.calls) as { peerId, answered, answer, close, ...metadata }, num}
  {peerId} - answered={answered} ({JSON.stringify(metadata)})
  <p>
    <button class="btn btn-success" on:click={close}>Close</button>
    {#if answered}
      <button class="btn btn-success" on:click={close}>Close</button>
    {:else}
      <button class="btn btn-success" on:click={answer}>Answer</button>
    {/if}
  </p>

  <hr class="h-px border-neutral" />
{/each}
