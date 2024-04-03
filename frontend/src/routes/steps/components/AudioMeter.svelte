<script>
  import { state } from "../../hit"
</script>

<div class="grid grid-cols-[auto_1fr_auto_1fr] items-center gap-3 px-2 text-base sm:px-6 sm:text-lg">
  <div><span class="hidden sm:contents">Microphone</span> 🎙</div>
  <div class="mr-4 sm:mr-8 md:mr-12">
    <progress class="progress progress-error sm:h-3" value={$state.micLevel} max="100"></progress>
  </div>
  <div class="ml-4 sm:ml-8 md:ml-12"><span class="hidden sm:contents">Speaker</span> 🔊</div>
  <div>
    <progress class="progress progress-success sm:h-3" value={$state.speakerLevel} max="100"></progress>
  </div>
</div>
