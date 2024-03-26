import { post } from "$lib/api"
import { Howl } from "howler"
import { get, writable } from "svelte/store"

const params = new URLSearchParams(window.location.search)
const assignment_id = params.get("assignmentId")
const hit_id = params.get("hitId")
const worker_id = params.get("workerId")
export const isPreview = assignment_id === "ASSIGNMENT_ID_NOT_AVAILABLE"
export const isDebug = !!+(params.get("debug") || 0)

const createState = () => {
  const { subscribe, set, update } = writable({
    ready: false,
    browserNotSupported: false,
    /** @type null | MediaStream */
    stream: null,
    failure: "",
    topic: "",
    /** Number[] */
    pin: { code: [], pin_audio_url: "", offsets: {} }
  })

  /** @type Howl */
  let pinAudio

  update(($state) => ({ ...$state, browserNotSupported: false }))
  // TODO if browser not supported: update($state => ({...$state, ready: true, browserNotSupported: true}))

  return {
    subscribe,
    async initialize() {
      if (!get({ subscribe }).ready) {
        const { success, data } = await post("hit/handshake", { assignment_id, hit_id, worker_id })
        if (!success) {
          update(($state) => ({ ...$state, failure: `Couldn't initialize! ${data.error}` }))
          return
        }
        const { topic, pin } = data
        pinAudio = new Howl({
          src: [pin.pin_audio_url],
          sprite: pin.offsets
        })

        update(($state) => ({ ...$state, ready: true, topic, pin }))
      }
    },
    async enableMic() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: { echoCancellation: true, autoGainControl: true, noiseSuppression: true },
          video: false
        })
        update(($state) => ({ ...$state, stream }))
        return { success: true, message: "Microphone enabled! " }
      } catch (e) {
        console.error("Error enabling media stream")
        return { success: false, message: "Error enabling microphone. Try again!" }
      }
    },
    playPin() {
      return new Promise((resolve) => {
        const {
          pin: { code, offsets }
        } = get({ subscribe })
        pinAudio.play(code[0])
        /** @type Number */
        let waitTime = offsets[code[0]][1]
        for (let i = 1; i < code.length; i++) {
          waitTime = waitTime + 175
          setTimeout(() => {
            pinAudio.play(code[i])
          }, waitTime)
          waitTime = waitTime + offsets[code[i]][1]
        }
        setTimeout(resolve, waitTime)
      })
    },
    /** @param {String} pin */
    async verifyPin(pin) {
      const { success, data } = await post("hit/pin", { pin: pin })
      return success && data.success
    },
    async recordWords() {
      const { stream } = get({ subscribe })
      console.log(stream)
      if (stream) {
        /** @type {any} */
        let timeout
        /** @type {BlobPart[]} */
        const chunks = []
        const recorder = new MediaRecorder(stream)
        recorder.onstop = () => {
          const blob = new Blob(chunks, { 'type' : recorder.mimeType });
          const formData = new FormData()
          console.log("posting")
          formData.append('audio', blob)
          post("hit/audio", formData)
        }
        recorder.ondataavailable = (e) => { chunks.push(e.data) }
        timeout = setTimeout(() => { recorder.stop() }, 10000)
        recorder.start()
      }
    }
  }
}

export const state = createState()
