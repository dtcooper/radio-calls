<script>
  import { state } from "../hit"

  const call = () => {
    state.call()
  }
</script>

<p>
  <button class="btn btn-neutral" on:click={call}>Call</button>
</p>
