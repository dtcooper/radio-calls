<script>
  import { state, isDebug } from "../hit"

  /** @type {(() => void) | null | undefined} */
  let stop

  /** @type {() => void} */
  export let next

  let playBtnDisabled = false
  let submitDisabled = false
  let recordDisabled = false
  let pinSuccess = false
  let pin = ""

  const playPin = async () => {
    playBtnDisabled = true
    await state.playPin()
    playBtnDisabled = false
  }

  const submitPin = async () => {
    submitDisabled = true
    pinSuccess = await state.verifyPin(pin)
    submitDisabled = false
  }

  const record = async () => {
    recordDisabled = true
    await state.recordWords()
    recordDisabled = false
  }
</script>

<p>
  <button class="btn btn-neutral" on:click={playPin} disabled={playBtnDisabled}>Play PIN</button>
</p>

<p>
  <input class="input input-bordered" bind:value={pin} disabled={submitDisabled} />
  <button class="btn btn-neutral" on:click={submitPin} disabled={submitDisabled}>Submit</button>
</p>

{#if pinSuccess || isDebug}
  <p>
    <button class="btn btn-neutral" on:click={record} disabled={recordDisabled}>Record</button>
  </p>
{/if}

{pin}
