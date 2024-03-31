import { createVolumeAnalyser, getMicAndInitAudio, initializePeer } from "$lib/utils"
import { get as _get, writable } from "svelte/store"

const createState = () => {
  const { subscribe, update: _update } = writable({
    failure: "",
    micLevel: 0,
    speakerLevel: 0,
    calls: {},
    hit: false,
    error: false
  })

  const update = (data) => _update(($state) => ({ ...$state, ...data }))
  const get = () => _get({ subscribe })
  let audioCtx, micMediaStream, peer, audioOut, audioOutAnalyserNode
  let audioOutNode = null

  return {
    subscribe,
    async initialize(hit, peerjsKey) {
      try {
        micMediaStream = await getMicAndInitAudio()
      } catch (e) {
        console.error("Error getting mic stream", e)
        update({ error: "Error getting mic!" })
        return
      }

      try {
        peer = await initializePeer(hit.peerId, peerjsKey)
      } catch (e) {
        if (e.type === "unavailable-id") {
          window.location.reload()
        }
        update({ error: `PeerJS Error: ${e}` })
      }

      let currentCall = null

      peer.on("call", (call) => {
        _update(($state) => {
          $state.calls[call.peer] = {
            ...call.metadata,
            peerId: call.peer,
            answered: false,
            close() {
              call.close()
            },
            answer() {
              call.answer(micMediaStream)
            }
          }
          return $state
        })

        call.on("stream", (stream) => {
          if (currentCall) {
            currentCall.close()
            currentCall = null
          }

          audioOut.srcObject = stream

          if (audioOutNode) {
            audioOutNode.disconnect()
            audioOutNode = null
          }

          audioOutNode = audioCtx.createMediaStreamSource(stream)
          audioOutNode.connect(audioOutAnalyserNode)

          currentCall = call
          _update(($state) => {
            $state.calls[call.peer] = { ...$state.calls[call.peer], answered: true }
            return $state
          })
        })

        call.on("close", () => {
          if (currentCall === call) {
            currentCall = null
          }

          _update(($state) => {
            delete $state.calls[call.peer]
            return $state
          })
        })
      })

      audioOut = document.createElement("audio")
      audioOut.crossOrigin = true
      audioOut.autoplay = true

      audioCtx = new AudioContext()

      const micNode = audioCtx.createMediaStreamSource(micMediaStream)
      const micAnalyser = createVolumeAnalyser(audioCtx, (volume) => update({ micLevel: volume }))
      micNode.connect(micAnalyser)

      audioOutAnalyserNode = createVolumeAnalyser(audioCtx, (volume) => update({ speakerLevel: volume }))

      update({ hit })
    }
  }
}

export const state = createState()
