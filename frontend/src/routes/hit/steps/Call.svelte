<script>
  import { runVolumeAnalyser } from "$lib/utils"
  import { Peer } from "peerjs"
  import { state } from "../hit"

  const peer = new Peer("c6d0a19c-9117-4867-8a92-80adb4895ac9", { secure: false, host: "127.0.0.1", port: 9000 })
  const context = new AudioContext()
  const audio = new Audio()
  peer.on("open", () => {
    console.log("connected")
  })

  const call = () => {
    console.log("calling")
    const call = peer.call("c6d0a19c-9117-4867-8a92-80adb4895ac8", $state.stream)
    call.on("stream", (remoteStream) => {
      audio.autoplay = true
      audio.srcObject = remoteStream
      runVolumeAnalyser(context.createMediaStreamSource(remoteStream), console.log)
    })
  }
</script>

<p>
  <button class="btn btn-neutral" on:click={call}>Call</button>
</p>
