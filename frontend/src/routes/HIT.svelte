<script>
  import { onMount, tick } from "svelte"
  import { slide } from "svelte/transition"

  import { persisted } from "svelte-persisted-store"

  import { state, levels, debugMode, isPreview } from "./hit"
  import Call from "./steps/Call.svelte"
  import ChooseName from "./steps/ChooseName.svelte"
  import Overview from "./steps/Overview.svelte"
  import Submit from "./steps/Submit.svelte"
  import TOS from "./steps/TOS.svelte"
  import AudioMeter from "./steps/components/AudioMeter.svelte"

  const darkTheme = persisted("dark-theme", false)
  $: document.documentElement.setAttribute("data-theme", $darkTheme ? "dark" : "light")
  let currentStep = 0

  const steps = [{ title: "Overview", component: Overview, emoji: "🔎", codeName: "overview", staffCanSkipTo: true }]

  if (!isPreview) {
    if ($debugMode) {
      currentStep = 3 // Call
    }
    steps.push(
      { title: "Terms of Service", component: TOS, emoji: "📜", codeName: "tos", staffCanSkipTo: true },
      { title: "Choose a Name", component: ChooseName, emoji: "👫", codeName: "name", staffCanSkipTo: true },
      { title: "Call", component: Call, emoji: "📞", codeName: "call", staffCanSkipTo: true },
      { title: "Submit", component: Submit, emoji: "💫", codeName: "done", staffCanSkipTo: false }
    )
  }

  $: step = steps[currentStep]

  const next = async () => {
    state.logProgress(`step: ${step.codeName} => ${steps[currentStep + 1].codeName}`)
    currentStep = currentStep + 1
    await tick() // Allows UI to update before scrolling
    window.scroll({ top: 0, behavior: "smooth" })
  }

  onMount(() => state.logProgress(`step: ${steps[0].codeName}`))
</script>

<!-- Dark mode and debug toggles -->
{#if $state.isStaff}
  <div
    class="tooltip tooltip-right fixed left-1 top-1 z-20"
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
  class="tooltip tooltip-left right-1 top-1 z-20 {$state.isStaff ? 'fixed' : 'absolute'}"
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
      <span class="hidden sm:contents">☎️🎉🎙️️📻</span>
      <span class="font-mono italic underline">Call a Radio Show</span>
      📻🎙️️🎉☎️
    </header>

    {#if steps.length > 1}
      <div class="sticky top-0 z-10 bg-base-100">
        <ul class="steps hidden px-1 pb-0.5 pt-2 sm:px-2 md:grid">
          {#each steps as { title, emoji, staffCanSkipTo }, num}
            {@const canSkip = $debugMode && staffCanSkipTo}
            <li data-content={emoji} class="step" class:step-info={num <= currentStep}>
              <!-- svelte-ignore a11y-no-static-element-interactions -->
              <svelte:element
                this={canSkip ? "button" : "span"}
                class="md:text-sm lg:text-base {num === currentStep ? 'font-bold text-info' : ''}"
                class:hover:text-primary={canSkip}
                on:click={() => {
                  if (canSkip) {
                    currentStep = num
                  }
                }}>{title}</svelte:element
              >
            </li>
          {/each}
        </ul>
        <div class="px-1 pb-0.5 pt-2 text-center font-bold sm:px-2 md:hidden">
          {step.emoji} Step {currentStep + 1} of {steps.length} &mdash; <span class="text-info">{step.title}</span>
        </div>

        <hr class="mx-3 mt-1 h-px border-neutral" />

        {#if step.component === Call}
          <div class="mt-2" transition:slide>
            <AudioMeter />
            <hr class="mx-3 mt-2 h-px border-neutral" />
          </div>
        {/if}
      </div>
    {/if}

    <main
      class="mb-3 mt-1 flex flex-1 flex-col gap-2 px-2 py-2 text-sm sm:gap-3 sm:px-3 sm:py-3 sm:text-base md:text-lg lg:text-xl"
    >
      <svelte:component this={step.component} {next} />
    </main>

    {#if !isPreview}
      <footer class="bg-base-200 py-0.5 text-center text-xs italic sm:text-sm md:text-base">
        Question? Comments? Concerns? Email
        <a href="mailto:david@jew.pizza" target="_blank" class="link-hover link link-accent">david@jew.pizza</a>.
      </footer>
    {/if}
  </div>

  {#if $debugMode}
    <pre class="hidden text-xs sm:block">state={JSON.stringify($state, null, 2)}
levels={JSON.stringify($levels, null, 2)}</pre>
  {/if}
</div>
