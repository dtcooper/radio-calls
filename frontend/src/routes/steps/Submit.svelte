<script>
  import { state } from "../hit"
  import NextButton from "./components/NextButton.svelte"
  import Notice from "./components/Notice.svelte"

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

<p class="text-center text-xl font-bold italic sm:text-2xl md:text-3xl">
  <span class="hidden sm:contents">🎉🎉🎉</span>
  <span class="font-mono text-success">Congratulations!</span> 🎉🎉🎉
</p>

<p>You have successfully completed the assignment! Click the button below to submit.</p>

<Notice warning={false}>
  <strong>REMEMBER:</strong> A <strong>silent call</strong> or <strong>voicemail</strong> where you did not speak will
  result in a <strong class="underline">REJECTED</strong> assignment!
</Notice>

<NextButton class="btn-accent" next={() => submit()} disabled={submitting}>Click here to submit! 💘</NextButton>

<form bind:this={form} method="post" action={$state.submitUrl} class="hidden">
  {#each ["assignmentId", "approvalCode", "name", "gender", "location"] as key}
    <input type="hidden" name={key} value={$state[key]} />
  {/each}
</form>
