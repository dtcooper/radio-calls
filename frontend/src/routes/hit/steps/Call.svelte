<script>
  import { state } from "../hit"

  export let next
</script>

<p>
  <button class="btn btn-primary" on:click={() => state.call()}>Call</button>
  <button class="btn btn-primary" on:click={() => state.call(true)}>Cheat</button>
</p>
