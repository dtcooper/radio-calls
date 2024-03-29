import { post, runVolumeAnalyser } from "$lib/utils"

import { noop } from "svelte/internal"
import { get as _get, writable } from "svelte/store"

import { persisted } from "svelte-persisted-store"

const params = new URLSearchParams(window.location.search)
const assignmentId = params.get("assignmentId")
const hitId = params.get("hitId")
const workerId = params.get("workerId")
export const isPreview = assignmentId === "ASSIGNMENT_ID_NOT_AVAILABLE"
export const debugMode = persisted("debug-mode", false)

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
    micLevel: 0,
    ready: false,
    speakerLevel: 0,
    pronouncer: [],
    topic: "",
    isStaff: false
  })

  let audioCtx, audioOut, micMediaStream, peerId, pronouncerWordList

  const update = (data) => _update(($state) => ({ ...$state, ...data }))
  const get = () => _get({ subscribe })

  // TODO if browser not supported: update($state => ({...$state, ready: true, browserNotSupported: true})

  return {
    subscribe,
    async initialize() {
      if (!get().ready) {
        const url = isPreview ? "hit/handshake/topic" : "hit/handshake"
        const { success, ...data } = await post(url, { assignmentId, hitId, workerId })
        if (!success) {
          update({ failure: `Couldn't initialize! ${data.error}` })
          canLeave = true
          return
        }

        const { topic, pronouncer, isStaff } = data

        if (isPreview) {
          update({ ready: true, topic, isStaff })
        } else {
          pronouncerWordList = pronouncer.wordList
          peerId = data.peerI
          audioOut = new Audio(pronouncer.audioUrl)

          update({ ready: true, topic, isStaff, pronouncer: pronouncer.words })
        }
      }
    },
    async initializeAudio() {
      if (get().audioInitialized) {
        return { success: true, message: "Audio already initialized!" }
      } else {
        try {
          audioCtx = new AudioContext()

          micMediaStream = await navigator.mediaDevices.getUserMedia({
            audio: { echoCancellation: true, autoGainControl: true },
            video: false
          })

          for (const action of ["play", "pause", "seekbackward", "seekforward", "previoustrack", "nexttrack"]) {
            navigator.mediaSession.setActionHandler(action, noop)
          }

          const outNode = audioCtx.createMediaElementSource(audioOut)
          outNode.connect(audioCtx.destination) // So we can hear it

          const micNode = audioCtx.createMediaStreamSource(micMediaStream)

          runVolumeAnalyser(micNode, (volume) => update({ micLevel: volume }))
          runVolumeAnalyser(outNode, (volume) => update({ speakerLevel: volume }))
          update({ audioInitialized: true })

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
          audioOut.currentTime = start
          audioOut.play()

          nextInterval = setInterval(() => {
            if (audioOut.currentTime >= end) {
              audioOut.pause()
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
    recordWords() {
      const abort = new AbortController()
      const { pronouncer } = get()
      const promise = new Promise((resolve) => {
        const chunks = []
        const recorder = new MediaRecorder(micMediaStream)
        recorder.onstop = async () => {
          const blob = new Blob(chunks, { type: recorder.mimeType })
          const formData = new FormData()
          formData.append("audio", blob)
          const { success, verified, heardWords, remotePeerId } = await post("hit/verify", formData)
          resolve({ success: success && verified, heardWords: heardWords || [] })
        }
        recorder.ondataavailable = (e) => chunks.push(e.data)
        setTimeout(() => recorder.stop(), 2500 * pronouncer.length) // 2.5 seconds per word
        abort.signal.onabort = () => recorder.stop()
        recorder.start()
      })
      return { abort, promise }
    }
  }
}

export const state = createState()
