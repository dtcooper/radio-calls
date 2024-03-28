import { post, runVolumeAnalyser } from "$lib/utils"
import { noop } from "svelte/internal"
import { get as _get, writable } from "svelte/store"

const params = new URLSearchParams(window.location.search)
const assignmentId = params.get("assignmentId")
const hitId = params.get("hitId")
const workerId = params.get("workerId")
export const isPreview = assignmentId === "ASSIGNMENT_ID_NOT_AVAILABLE"
export const isDebug = !!+(params.get("debug") || 0)

const createState = () => {
  const {
    subscribe,
    set,
    update: _update
  } = writable({
    audioInitialized: false,
    browserNotSupported: false,
    failure: "",
    micLevel: 0,
    pin: { code: [], audioUrl: "", offsets: {} },
    pronouncer: [],
    ready: false,
    speakerLevel: 0,
    topic: ""
  })

  let audioCtx, audioOut, micStream

  const update = (data) => _update(($state) => ({ ...$state, ...data }))
  const get = () => _get({ subscribe })

  update(($state) => ({ ...$state, browserNotSupported: false }))
  // TODO if browser not supported: update($state => ({...$state, ready: true, browserNotSupported: true}))

  return {
    subscribe,
    async initialize() {
      if (!get().ready) {
        const { success, ...data } = await post("handshake", { assignmentId, hitId, workerId })
        if (!success) {
          update({ failure: `Couldn't initialize! ${data.error}` })
          return
        }
        const { topic, pin, pronouncer } = data

        audioOut = new Audio(pin.audioUrl)

        update({ ready: true, topic, pin, pronouncer })
      }
    },
    async initializeAudio() {
      if (get().audioInitialized) {
        return { success: true, message: "Audio already initialized!" }
      } else {
        try {
          audioCtx = new AudioContext()

          micStream = await navigator.mediaDevices.getUserMedia({
            audio: { echoCancellation: true, autoGainControl: true, noiseSuppression: true },
            video: false
          })

          for (const action of ["play", "pause", "seekbackward", "seekforward", "previoustrack", "nexttrack"]) {
            navigator.mediaSession.setActionHandler(action, noop)
          }

          const outStream = audioCtx.createMediaElementSource(audioOut)
          outStream.connect(audioCtx.destination)

          runVolumeAnalyser(audioCtx.createMediaStreamSource(micStream), (volume) => update({ micLevel: volume }))
          runVolumeAnalyser(outStream, (volume) => update({ speakerLevel: volume }))
          update({ audioInitialized: true })

          return { success: true, message: "Microphone enabled! " }
        } catch (e) {
          console.error("Error enabling media stream")
          return { success: false, message: "Error enabling microphone. Try again!" }
        }
      }
    },
    playPin() {
      return new Promise((resolve) => {
        // Bad looking code on purpose!
        const {
          pin: { code, offsets }
        } = get()
        let a = audioOut,
          n = 0,
          i,
          t
        const p = () => {
          const [s, l] = offsets[code[n++]]
          a.currentTime = s / 1000
          a.play()
          i = setInterval(() => {
            if (audioOut.currentTime > (s + l) / 1000) {
              audioOut.pause()
              clearInterval(i)
              if (n >= code.length) {
                clearTimeout(t)
                resolve()
              } else {
                setTimeout(() => p(), 150)
              }
            }
          }, 10)
        }
        // Maybe something wonky happened?
        t = setTimeout(() => {
          clearInterval(i)
          resolve()
        }, 8000)
        p()
      })
    },
    async verifyPin(pin) {
      const { success, accepted } = await post("verify/pin", { pin: pin })
      return success && accepted
    },
    async recordWords() {
      if (micStream) {
        let timeout
        const chunks = []
        const recorder = new MediaRecorder(micStream)
        recorder.onstop = () => {
          clearTimeout(timeout)
          const blob = new Blob(chunks, { type: recorder.mimeType })
          const formData = new FormData()
          console.log("posting")
          formData.append("audio", blob)
          post("verify/pronouncer", formData)
        }
        recorder.ondataavailable = (e) => chunks.push(e.data)
        timeout = setTimeout(() => {
          recorder.stop()
        }, 3500)
        recorder.start()
      }
    }
  }
}

export const state = createState()
