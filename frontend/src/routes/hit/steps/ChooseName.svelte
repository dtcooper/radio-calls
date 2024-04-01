<script>
  import { title } from "$lib/utils"
  import { state } from "../hit"

  export let next

  let gender = $state.gender
  let name = $state.name
  let placeholder

  const submit = () => {
    if (gender !== $state.gender || name !== $state.name) {
      state.updateName(name, gender)
    }
    next()
  }

  $: if (gender === "other") {
    placeholder = "Pat Doe"
  } else if (gender === "female") {
    placeholder = "Jane Doe"
  } else {
    placeholder = "John Doe"
  }
</script>

<p>Now it's time to choose a name. The person you'll be talking to will refer to you as this name.</p>

<p>You are encouraged <strong>NOT</strong> to use your real name and to make something up.</p>

<div
  class="mx-4 mt-3 grid grid-cols-[max-content_1fr] items-center gap-x-5 gap-y-8 border-l-2 border-l-neutral py-2 pl-2 sm:mx-4 sm:pl-4 md:mx-12"
>
  <div class="text-right font-bold">Name</div>
  <div>
    <input
      class="input input-sm input-info w-full sm:input-md md:input-lg md:mr-0 md:w-4/5 lg:w-2/3"
      {placeholder}
      maxlength={$state.nameMaxLength}
      bind:value={name}
    />
  </div>
  <div class="text-right font-bold">Gender</div>
  <div class="flex items-center gap-8">
    {#each [["💁‍♂️", "male"], ["💁‍♀️", "female"], ["💁", "other"]] as [emoji, value]}
      <label class="flex cursor-pointer items-center gap-2">
        <input type="radio" name="gender" class="radio-info radio radio-sm lg:radio-md" bind:group={gender} {value} />
        {emoji} <span class:text-info={value === gender} class:underline={value === gender}>{title(value)}</span>
      </label>
    {/each}
  </div>
</div>

<p class="text-center mt-2">
  <button class="btn btn-success btn-xs sm:btn-sm md:btn-lg" disabled={name.length < 1} on:click={submit}>
    Continue with assignment
  </button>
</p>
