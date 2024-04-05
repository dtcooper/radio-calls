<script>
  import { state } from "../hit"
  import NextButton from "./components/NextButton.svelte"

  let form
  let submitting = false
  const submit = async () => {
    submitting = true
    const success = await state.finalize()
    if ($state.submitUrl) {
      if (success) {
        form.submit()
      } else {
        state.setFailure(
          "An error occurred while submitting this assignment. Try again. If it persists, contact the HIT author david@jew.pizza."
        )
        submitting = false
      }
    } else {
      const formData = new FormData(form)
      alert(
        `You are getting this popup because no turkSubmitTo was supplied.\n\n[Accepted: ${success}]\n` +
          Array.from(formData.entries())
            .map(([key, value]) => `${key}: ${value}`)
            .join("\n")
      )
      submitting = false
    }
  }

  $$restProps // silence: <Submit> was created with unknown prop 'next'
</script>

<NextButton class="btn-info" next={() => submit()} disabled={submitting}>Submit</NextButton>

<form bind:this={form} method="post" action={$state.submitUrl} class="hidden">
  {#each ["assignmentId", "approvalCode", "name", "gender", "location"] as key}
    <input type="hidden" name={key} value={$state[key]} />
  {/each}
</form>
