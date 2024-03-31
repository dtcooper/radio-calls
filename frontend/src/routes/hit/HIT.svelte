<script>
  import { tick } from "svelte"
  import { slide } from "svelte/transition"

  import { persisted } from "svelte-persisted-store"

  import { state, debugMode } from "./hit"
  import Call from "./steps/Call.svelte"
  import InitializeAudio from "./steps/InitializeAudio.svelte"
  import Overview from "./steps/Overview.svelte"
  import Submit from "./steps/Submit.svelte"
  import TOS from "./steps/TOS.svelte"
  import Verify from "./steps/Verify.svelte"

  import { isPreview } from "./hit"

  const darkTheme = persisted("dark-theme", false)
  $: document.documentElement.setAttribute("data-theme", $darkTheme ? "dark" : "light")
  let currentStep = 0

  const steps = [{ title: "Overview", component: Overview, emoji: "🔎" }]
  if (!isPreview) {
    if ($debugMode) {
      currentStep = 2 // Microphone
    }
    steps.push(
      { title: "Terms of Service", component: TOS, emoji: "📜" },
      { title: "Microphone", component: InitializeAudio, emoji: "🎙" },
      { title: "Verifications", component: Verify, emoji: "⚖️" },
      { title: "Call", component: Call, emoji: "📞" },
      { title: "Submit", component: Submit, emoji: "💫" }
    )
  }

  const next = async () => {
    currentStep = currentStep + 1
    await tick()
    window.scroll({ top: 0, behavior: "smooth" })
  }

  $: step = steps[currentStep]
</script>

<!-- Dark mode and debug toggles -->
{#if $state.isStaff}
  <div
    class="tooltip tooltip-right fixed left-1 top-1 z-10"
    class:tooltip-info={!$darkTheme}
    data-tip="Enable {$debugMode ? 'regular' : 'debug'} mode"
  >
    <button class="btn btn-circle btn-ghost btn-xs sm:btn-sm" on:click={() => ($debugMode = !$debugMode)}>
      <span class="text-sm sm:text-lg"
        >{#if $debugMode}✋{:else}🧪{/if}</span
      >
    </button>
  </div>
{/if}
<div
  class="tooltip tooltip-left right-1 top-1 z-10 {$state.isStaff ? 'fixed' : 'absolute'}"
  class:tooltip-info={!$darkTheme}
  data-tip="Enable {$darkTheme ? 'light' : 'dark'} theme"
>
  <button class="btn btn-circle btn-ghost btn-xs sm:btn-sm" on:click={() => ($darkTheme = !$darkTheme)}>
    <span class="text-sm sm:text-lg"
      >{#if $darkTheme}☀️{:else}🌙{/if}</span
    >
  </button>
</div>

<div class="bg-base-200">
  <!-- Main content -->
  <div class="mx-auto flex min-h-screen max-w-screen-lg flex-col rounded-b-2xl bg-base-100">
    <header class="mb-2 px-1 pt-2 text-center text-2xl font-bold sm:px-2 sm:pt-3 sm:text-3xl md:text-4xl">
      <span class="hidden sm:contents">🎉🎙️️📻</span>
      <span class="font-mono italic underline">Call a Radio Show</span>
      📻🎙️️🎉
    </header>

    {#if steps.length > 1}
      <div class="sticky top-0 z-10 bg-base-100">
        <ul class="steps hidden px-1 pb-0.5 pt-2 sm:px-2 md:grid">
          {#each steps as { title, emoji }, num}
            <li data-content={emoji} class="step" class:step-info={num <= currentStep}>
              <span class="md:text-sm lg:text-base {num === currentStep ? 'font-bold text-info' : ''}">{title}</span>
            </li>
          {/each}
        </ul>
        <div class="px-1 pb-0.5 pt-2 text-center font-bold sm:px-2 md:hidden">
          {step.emoji} Step {currentStep + 1} of {steps.length} &mdash; <span class="text-info">{step.title}</span>
        </div>

        <hr class="mx-3 mt-1 h-px border-neutral" />

        {#if $state.audioInitialized}
          <div
            class="mt-2 grid grid-cols-[auto_1fr_auto_1fr] items-center gap-3 px-2 text-base sm:px-6 sm:text-lg"
            transition:slide
          >
            <div><span class="hidden sm:contents">Microphone</span> 🎙</div>
            <div class="mr-4 sm:mr-8 md:mr-12">
              <progress class="progress progress-error sm:h-3" value={$state.micLevel} max="100"></progress>
            </div>
            <div class="ml-4 sm:ml-8 md:ml-12"><span class="hidden sm:contents">Speaker</span> 🔊</div>
            <div>
              <progress class="progress progress-success sm:h-3" value={$state.speakerLevel} max="100"></progress>
            </div>
          </div>
          <hr class="mx-3 mt-2 h-px border-neutral" />
        {/if}
      </div>
    {/if}

    <main
      class="mb-3 mt-1 flex flex-1 flex-col gap-2 px-2 py-2 text-sm sm:gap-3 sm:px-3 sm:py-3 sm:text-base md:text-lg lg:text-xl"
    >
      <svelte:component this={step.component} {next} />
    </main>
  </div>

  <footer class="mt-1 bg-base-200 text-center italic">
    Question? Comments? Concerns? Email
    <a href="mailto:david@jew.pizza" target="_blank" class="link-hover link link-accent">david@jew.pizza</a>.
  </footer>

  {#if $debugMode}
    <pre class="text-xs">{JSON.stringify($state, null, 2)}</pre>
  {/if}
</div>
