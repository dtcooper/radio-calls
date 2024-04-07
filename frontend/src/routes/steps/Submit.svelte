<script>
  import { onMount } from "svelte"
  import { slide } from "svelte/transition"
  import { state } from "../hit"
  import NextButton from "./components/NextButton.svelte"
  import Notice from "./components/Notice.svelte"

  let feedbackExpanded = false
  let feedback = ""
  let form
  let submitting = false
  const submit = async () => {
    submitting = true
    const success = await state.finalize({ feedback })
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
      state.logProgress("fake submit assignment")
    }
  }

  onMount(() => state.logProgress("on submit page"))

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

<details
  class="collapse collapse-arrow bg-base-200 {feedbackExpanded || feedback
    ? ''
    : 'animate-highlight-shadow shadow-base-300'}"
  bind:open={feedbackExpanded}
>
  <summary class="collapse-title font-medium hover:bg-base-300">
    <span>Click here to leave additional feedback</span>
    <span class="text-xs font-normal italic sm:text-sm">
      (<span class="text-success">$$$</span> A bonus may be awarded if you leave feedback!
      <span class="text-success">$$$</span>)
    </span>
  </summary>
  <div class="collapse-content" transition:slide>
    <label class="form-control">
      <div class="label">
        <span class="label-text">Enter your feedback below</span>
      </div>
      <textarea
        class="textarea textarea-bordered textarea-sm h-24 md:textarea-lg md:h-36"
        placeholder="Any additional feedback can be provided here..."
        bind:value={feedback}
        disabled={submitting}
      />
    </label>
  </div>
</details>

<NextButton class="btn-accent" next={() => submit()} disabled={submitting}>Click here to submit! 💘</NextButton>

<form bind:this={form} method="post" action={$state.submitUrl} class="hidden">
  <input type="hidden" name="name" value="{$state.name} [{$state.gender.substr(0, 1).toUpperCase()}]" />
  {#each ["assignmentId", "approvalCode", "location", "callDurationSeconds", "feedback"] as key}
    <input type="hidden" name={key} value={$state[key]} />
  {/each}
</form>
