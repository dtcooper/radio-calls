<script>
  import { state } from "../hit"
  let form

  $$restProps // Ignore unused next
</script>

<p>
  <button class="btn btn-neutral" on:click={form.submit()}>Submit</button>
</p>

<form bind:this={form} method="post" action={$state.submitUrl} class="hidden">
  <input type="hidden" name="assignmentId" value={$state.assignmentId} />
  <input type="hidden" name="approvalCode" value="TODO" />
</form>
