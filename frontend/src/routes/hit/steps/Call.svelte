<script>
  import { state } from "../hit"

  export let next
</script>

<p>
  <button class="btn btn-success" on:click={() => state.call()} disabled={$state.callInProgress}>Call</button>
  <button class="btn btn-secondary" on:click={() => state.call(true)} disabled={$state.callInProgress}>Cheat</button>
  <button class="btn btn-error" on:click={() => state.hangup()} disabled={!$state.callInProgress}>Hangup</button>
</p>
