import { createVolumeAnalyser, getMicAndInitAudio, initializePeer, post } from "$lib/utils"
import { persisted } from "svelte-persisted-store"
import { get as _get, writable } from "svelte/store"

const params = new URLSearchParams(window.location.search)
const assignmentId = params.get("assignmentId")
const hitId = params.get("hitId")
const workerId = params.get("workerId")
export const isPreview = assignmentId === "ASSIGNMENT_ID_NOT_AVAILABLE"
export const debugMode = persisted("debug-mode", false)
const isDebug = () => _get(debugMode)

let canLeave = false

window.onbeforeunload = () =>
  canLeave || _get(debugMode) ? undefined : "Are you sure you want to leave this assignment?"
export const reload = () => {
  canLeave = true
  window.location.reload()
}

const createState = () => {
  const { subscribe, update: _update } = writable({
    audioInitialized: false,
    failure: "",
    isStaff: false,
    micLevel: 0,
    pronouncer: [],
    ready: false,
    remotePeerId: "",
    speakerLevel: 0,
    topic: ""
  })

  let audioCtx,
    pronouncerAudio,
    audioOut,
    audioOutNode = null,
    micMediaStream,
    pronouncerWordList,
    peer,
    remotePeerId,
    call,
    outputAnalyser

  const update = (data) => _update(($state) => ({ ...$state, ...data }))
  const get = () => _get({ subscribe })
  const fatalError = (msg, e) => {
    if (e && isDebug()) {
      msg += ` [Error: ${e}]`
    }
    update({ failure: msg })
    canLeave = true
  }

  // TODO if browser not supported: update($state => ({...$state, ready: true, browserNotSupported: true})

  return {
    subscribe,
    async initialize() {
      if (!get().ready) {
        try {
          const url = isPreview ? "hit/handshake/topic" : "hit/handshake"
          const { success, ...data } = await post(url, { assignmentId, hitId, workerId })
          if (!success) {
            fatalError(`Couldn't initialize! ${data.error}`)
            return
          }

          const { topic, pronouncer, isStaff, peerId, peerjsKey } = data

          if (!isStaff) {
            debugMode.set(false)
          }

          if (isPreview) {
            update({ ready: true, topic, isStaff })
          } else {
            pronouncerWordList = pronouncer.wordList

            try {
              peer = await initializePeer(peerId, peerjsKey)
            } catch (e) {
              fatalError("Couldn't connect to server. Please try again.", e)
              return
            }

            pronouncerAudio = document.createElement("audio")
            pronouncerAudio.src = pronouncer.audioUrl

            audioOut = document.createElement("audio")
            audioOut.autoplay = true

            update({ ready: true, topic, isStaff, pronouncer: pronouncer.words })
          }
        } catch (e) {
          fatalError("An unexpected error occurred and we couldn't initialize!", e)
        }
      }
    },
    async initializeAudio() {
      if (get().audioInitialized) {
        return { success: true, message: "Audio already initialized!" }
      } else {
        try {
          audioCtx = new AudioContext()
          micMediaStream = await getMicAndInitAudio()

          const micNode = audioCtx.createMediaStreamSource(micMediaStream)

          const micAnalyser = createVolumeAnalyser(audioCtx, (volume) => update({ micLevel: volume }))
          micNode.connect(micAnalyser)
          update({ audioInitialized: true })

          const pronouncerNode = audioCtx.createMediaElementSource(pronouncerAudio)
          outputAnalyser = createVolumeAnalyser(audioCtx, (volume) => update({ speakerLevel: volume }))
          pronouncerNode.connect(outputAnalyser)
          outputAnalyser.connect(audioCtx.destination)

          return { success: true, message: "Microphone enabled!" }
        } catch (e) {
          console.error("Error enabling media stream", e)
          return { success: false, message: "Error enabling microphone. Try again!" }
        }
      }
    },
    playPronouncer() {
      return new Promise((resolve) => {
        const { pronouncer } = get()
        const speakingGap = 150
        let wordIndex = 0
        let nextInterval
        let resetTimeout
        const play = () => {
          const word = pronouncer[wordIndex++]
          const { start, end } = pronouncerWordList[word]
          pronouncerAudio.currentTime = start
          pronouncerAudio.play()

          nextInterval = setInterval(() => {
            if (pronouncerAudio.currentTime >= end) {
              pronouncerAudio.pause()
              clearInterval(nextInterval)
              if (wordIndex >= pronouncer.length) {
                clearTimeout(resetTimeout)
                resolve()
              } else {
                setTimeout(() => play(), speakingGap)
              }
            }
          }, 15)
        }
        // Maybe something wonky happened? Timeout
        resetTimeout = setTimeout(
          () => {
            clearInterval(nextInterval)
            resolve()
          },
          (1250 + speakingGap) * pronouncer.length
        )

        play()
      })
    },
    recordVerifySubmit() {
      const abort = new AbortController()
      const { pronouncer } = get()
      const promise = new Promise((resolve) => {
        const chunks = []
        const recorder = new MediaRecorder(micMediaStream)
        recorder.onstop = async () => {
          const blob = new Blob(chunks, { type: recorder.mimeType })
          const formData = new FormData()
          formData.append("audio", blob)
          const { success, verified, heardWords, remotePeerId: _remotePeerId } = await post("hit/verify", formData)
          remotePeerId = _remotePeerId
          resolve({ success: success && verified, heardWords: heardWords || [] })
        }
        recorder.ondataavailable = (e) => chunks.push(e.data)
        setTimeout(() => recorder.stop(), 2500 * pronouncer.length) // 2.5 seconds per word
        abort.signal.onabort = () => recorder.stop()
        recorder.start()
      })
      return { abort, promise }
    },
    async cheatVerifySubmit() {
      const { success, verified, remotePeerId: _remotePeerId } = await post("hit/verify/cheat")
      remotePeerId = _remotePeerId
      return success && verified
    },
    call() {
      outputAnalyser.disconnect()

      return new Promise((accept, reject) => {
        call = peer.call(remotePeerId, micMediaStream, { metadata: { hi: "mom" } })
        console.log("Placing call to ", remotePeerId)
        call.on("stream", (stream) => {
          if (audioOutNode) {
            audioOutNode.disconnect()
          }
          audioOut.autoplay = true
          audioOut.srcObject = stream

          audioOutNode = audioCtx.createMediaStreamSource(stream)
          audioOutNode.connect(outputAnalyser)

          accept()
        })
        call.on("close", (e) => {
          console.warn("CALL CLOSED", e)
        })
        call.on("error", (e) => {
          console.warn("CALL ERROR", e)
        })
      })
    }
  }
}

export const state = createState()
