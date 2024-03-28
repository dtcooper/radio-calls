<script>
  import { tick } from "svelte"

  import { state } from "./hit"
  import Call from "./steps/Call.svelte"
  import EnableMic from "./steps/EnableMic.svelte"
  import Overview from "./steps/Overview.svelte"
  import Submit from "./steps/Submit.svelte"
  import TOS from "./steps/TOS.svelte"
  import TestSpeaking from "./steps/TestSpeaking.svelte"

  import { isPreview } from "./hit"

  let stepNumber = 2

  let main
  const steps = [{ title: "Overview", component: Overview, emoji: "🔎" }]
  if (!isPreview) {
    steps.push(
      { title: "Terms of Service", component: TOS, emoji: "📜" },
      { title: "Enable Microphone", component: EnableMic, emoji: "🎙" },
      { title: "Test Speaking", component: TestSpeaking, emoji: "?" },
      { title: "Call", component: Call, emoji: "📞" },
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

    {#if $state.audioInitialized}
      <div class="grid grid-cols-[auto_1fr_auto_1fr] items-center gap-3 px-2 text-base sm:px-6 sm:text-lg">
        <div><span class="hidden sm:inline">Microphone</span> 🎙</div>
        <div class="mr-4 sm:mr-8 md:mr-12">
          <progress class="progress progress-error sm:h-3" value={$state.micLevel} max="100"></progress>
        </div>
        <div class="ml-4 sm:ml-8 md:ml-12"><span class="hidden sm:inline">Speaker</span> 🔊</div>
        <div>
          <progress class="progress progress-success rotate-180 sm:h-3" value={$state.speakerLevel} max="100"
          ></progress>
        </div>
      </div>
      <hr class="mx-3 my-2 h-px bg-base-300" />
    {/if}

    <main
      bind:this={main}
      class="flex flex-1 flex-col gap-5 overflow-y-auto px-2 pb-0.5 pt-2 text-sm sm:px-3 sm:pt-3 sm:text-base md:text-lg lg:text-xl"
    >
      <svelte:component this={step.component} {next} />
    </main>

    <footer class="text-center italic">
      Question? Comments? Concerns? Email
      <a href="mailto:david@jew.pizza" target="_blank" class="link-hover link link-accent">david@jew.pizza</a>.
    </footer>
  </div>
</div>
