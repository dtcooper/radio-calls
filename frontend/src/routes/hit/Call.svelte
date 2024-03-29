<script>
  import { tick } from "svelte"

  import EnableMic from "./steps/EnableMic.svelte"
  import Overview from "./steps/Overview.svelte"
  import Submit from "./steps/Submit.svelte"
  import TOS from "./steps/TOS.svelte"
  import TestSpeaking from "./steps/TestSpeaking.svelte"

  import { isPreview } from "./hit"

  let stepNumber = 2
  /** @type {HTMLElement} */
  let main
  const steps = [{ title: "Overview", component: Overview, emoji: "🔎" }]
  if (!isPreview) {
    steps.push(
      { title: "Terms of Service", component: TOS, emoji: "📜" },
      { title: "Enable Microphone", component: EnableMic, emoji: "🎙" },
      { title: "Test Speaking", component: TestSpeaking, emoji: "?" },
      { title: "Submit", component: Submit, emoji: "💫" }
    )
  }

  const next = async () => {
    stepNumber = stepNumber + 1
    await tick()
    main?.scroll({ top: 0, behavior: "smooth" })
  }

  $: step = steps[stepNumber]
</script>

<div class="h-screen w-screen bg-base-200">
  <div class="mx-auto flex h-full w-full max-w-screen-lg flex-col gap-2 bg-base-100">
    <header class="px-1 pb-0.5 pt-2 text-center font-mono text-2xl font-bold sm:px-2 sm:pt-3 sm:text-3xl md:text-4xl">
      <span class="hidden sm:inline">🎉🎙️️📻</span>
      <span class="italic underline">Call a Radio Show</span>
      📻🎙️️🎉
    </header>

    {#if steps.length > 1}
      <ul class="steps mt-3 hidden px-1 pb-0.5 pt-2 sm:px-2 md:grid">
        {#each steps as { title, emoji }, num}
          <li data-content={emoji} class="step" class:step-primary={num <= stepNumber}>{title}</li>
        {/each}
      </ul>
      <div class="mt-2 px-1 pb-0.5 pt-2 text-center font-bold text-primary sm:px-2 sm:pt-3 md:hidden">
        {step.emoji} Step {stepNumber + 1} / {steps.length}: {step.title}
      </div>
    {/if}

    <hr class="mx-3 my-2 h-px bg-base-300" />

    <main
      bind:this={main}
      class="flex flex-1 flex-col gap-5 overflow-y-auto px-1 pb-0.5 pt-2 text-sm sm:px-2 sm:pt-3 sm:text-base md:text-lg lg:text-xl"
    >
      <svelte:component this={step.component} {next} />
    </main>

    <footer class="text-center italic">
      Question? Comments? Concerns? Email
      <a href="mailto:david@jew.pizza" target="_blank" class="link-hover link link-accent">david@jew.pizza</a>.
    </footer>
  </div>
</div>
