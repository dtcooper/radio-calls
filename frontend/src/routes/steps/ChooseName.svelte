<script>
  import NextButton from "./components/NextButton.svelte"
  import Notice from "./components/Notice.svelte"

  import { title } from "$lib/utils"
  import { state, scroll } from "../hit"

  export let next

  let gender = $state.gender
  let name = $state.name

  const submit = () => {
    if (gender !== $state.gender || name !== $state.name) {
      state.updateName(name, gender)
    }
    next()
  }
</script>

<p>Now it's time to choose a name. The person you'll be talking to will refer to you as this name.</p>

<p>You are should <strong class="underline">NOT</strong> to use your real name. Make something up.</p>

<Notice>
  <strong>NOTICE:</strong>
  Revealing your real name is against Amazon Mechanical Turk's Acceptable Use Policy! That's why we've assigned you a random
  one below.
</Notice>

<p class="italic text-primary">
  We've assigned you a <strong>random name</strong> and <strong>gender</strong> below, but you're are
  <strong>encouraged change it!</strong>
</p>

<div
  class="mx-4 mt-3 grid grid-cols-[max-content_1fr] items-baseline gap-x-5 gap-y-6 border-l-2 border-l-neutral py-2 pl-2 sm:mx-4 sm:pl-4 md:mx-12"
>
  <div class="text-right font-bold">First Name:</div>
  <div>
    <label class="form-control w-full max-w-md">
      <input
        class="input input-sm input-info w-full sm:input-md md:input-lg"
        maxlength={$state.nameMaxLength}
        bind:value={name}
        on:focus={(e) => scroll(e.target)}
      />
      <div class="label justify-end">
        <span class="label-text-alt sm:mr-3">This is the name you'll be called during your conversation.</span>
      </div>
    </label>
  </div>
  <div class="self-center text-right font-bold">Gender:</div>
  <div>
    <div class="grid grid-cols-[min-content] gap-1">
      <div class="flex flex-col items-start gap-2 sm:flex-row sm:items-center sm:gap-8">
        {#each [["💁‍♂️", "male"], ["💁‍♀️", "female"], ["💁", "other"]] as [emoji, value]}
          <label class="flex cursor-pointer items-center gap-2">
            <input
              type="radio"
              name="gender"
              class="radio-info radio radio-sm lg:radio-md"
              bind:group={gender}
              {value}
            />
            {emoji} <span class:text-info={value === gender} class:underline={value === gender}>{title(value)}</span>
          </label>
        {/each}
      </div>
      <div class="mr-3 hidden text-right text-xs sm:block">Choose a gender that best matches your name.</div>
    </div>
  </div>
</div>

<NextButton disabled={name.length < 1} next={submit} />
