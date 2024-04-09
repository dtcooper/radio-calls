import { Device } from "@twilio/voice-sdk"
import { persisted } from "svelte-persisted-store"
import { get as _get, derived, readonly, writable } from "svelte/store"

import { CALL_STEP_CALL, CALL_STEP_DONE, CALL_STEP_INITIAL, CALL_STEP_VOICEMAIL } from "$lib/shared-constants.json"
import { post as _post } from "$lib/utils"
import dayjs from "dayjs"
import { default as dayjsPluginDuration } from "dayjs/plugin/duration"
import { default as dayjsPluginRelativeTime } from "dayjs/plugin/relativeTime"

dayjs.extend(dayjsPluginDuration)
dayjs.extend(dayjsPluginRelativeTime)

const params = new URLSearchParams(window.location.search)
let assignmentId = params.get("assignmentId")
let hitId = params.get("hitId")
let workerId = params.get("workerId")
const turkSubmitTo = params.get("turkSubmitTo") || null
let dbId = params.get("dbId")

export const darkTheme = persisted("dark-theme", false)
export const isPreview = assignmentId === "ASSIGNMENT_ID_NOT_AVAILABLE"
export const debugMode = persisted("debug-mode", false)

const isDebug = () => _get(debugMode)
const log = (...args) => isDebug() && console.log(...args)
const warn = (...args) => isDebug() && console.warn(...args)

export const scroll = (elemOrId) => {
  const elem = typeof elemOrId === "string" ? document.getElementById(elemOrId) : elemOrId
  elem?.scrollIntoView({ behavior: "smooth", block: "center" })
}

// Every endpoint takes the assignment ID
const post = (endpoint, data) => _post(endpoint, { assignmentId, ...data }, isDebug())

// Separate store for levels because this gets written to a lot
const levelsFuzzAmount = 1.35
const levels = writable({ speaker: 0, mic: 0 })
const readonlyLevels = readonly(levels)
export { readonlyLevels as levels }

const createState = () => {
  const { subscribe, update: _update } = writable({
    approvalCode: "invalid-approval-code",
    assignmentId: "",
    callDurationSeconds: 0,
    callInProgress: false,
    callStep: CALL_STEP_INITIAL,
    countdown: null,
    estimatedBeforeVerifiedDuration: null,
    failure: "",
    feedback: "",
    gender: "",
    hitId: null,
    isProd: true,
    isStaff: false,
    leaveVoicemailAfterDuration: null,
    location: "",
    minCallDuration: null,
    name: "",
    nameMaxLength: 0,
    now: dayjs(),
    ready: false,
    showHost: "",
    submitUrl: "",
    topic: "",
    wordsHeard: "",
    workerId: null
  })

  const update = (data) => _update(($state) => ({ ...$state, ...data }))
  const showError = (msg) => update({ failure: msg })
  const fatalError = (msg) => update({ failure: msg, ready: false })

  setInterval(() => update({ now: dayjs() }), 250) // Up-to-date ish dayjs object for intervals
  const { subscribe: subscribeDerived } = derived({ subscribe }, ($state) => {
    let countdownDuration = null
    if ($state.countdown) {
      countdownDuration = dayjs.duration(Math.max($state.countdown.diff($state.now), 0))
    }

    const done =
      $state.callStep === CALL_STEP_DONE || ($state.callStep === CALL_STEP_VOICEMAIL && !$state.callInProgress)
    const canHangUp =
      $state.callInProgress &&
      (isDebug() ||
        [CALL_STEP_DONE, CALL_STEP_VOICEMAIL].includes($state.callStep) ||
        ($state.callStep == CALL_STEP_CALL && $state.now.isAfter($state.countdown)))

    return { ...$state, countdownDuration, canHangUp, done }
  })

  const get = () => _get({ subscribe: subscribeDerived })

  window.dayjs = dayjs // XXX

  /** @type {Device} */
  let device

  /** @type {import("@twilio/voice-sdk").Call}} */
  let call = null
  return {
    subscribe: subscribeDerived,
    async initialize() {
      if (!get().ready) {
        let url = "handshake"
        if (isPreview) {
          url += "/preview"
        }
        const { success, ...data } = await post(url, {
          hitId,
          workerId,
          dbId,
          isPreview,
          userAgent: navigator.userAgent
        })
        if (!success) {
          fatalError(`Couldn't initialize! ${data.error}`)
          this.logProgress("Handshake failed!")
          return
        }

        const { isStaff, token, ...rest } = data

        if (isStaff) {
          // In case we're staff, these may have been sent back by server if unspecified
          ;({ assignmentId, hitId, workerId } = data)
          if (!hitId) {
            warn("hitId was returned as null. This assignment doesn't appear to be actually hosted on Amazon.")
          }
        } else {
          debugMode.set(false)
        }

        if (!isPreview) {
          this.logProgress("handshake")
          this.createDevice(token)
          for (const [name, store] of [
            ["darkTheme", darkTheme],
            ["debugMode", debugMode]
          ]) {
            let changed = false // Don't run on first subscribe
            store.subscribe((value) => {
              if (changed) {
                this.logProgress(`ui change ${name}=${value}`)
              } else {
                changed = true
              }
            })
          }
        }

        for (const [key, value] of Object.entries(rest)) {
          if (key.endsWith("Duration")) {
            rest[key] = dayjs.duration(value)
          }
        }

        update({
          ready: true,
          isStaff,
          submitUrl: turkSubmitTo && `${turkSubmitTo}/mturk/externalSubmit`,
          ...rest
        })

        log("initial state:", get())
      }
    },
    async refreshToken() {
      const { success, token } = await post("token")
      if (success) {
        device.updateToken(token)
        this.logProgress("update token")
      } else {
        this.logProgress("update token FAILURE!")
      }
    },
    createDevice(token) {
      device = new Device(token, { closeProtection: true })
      device.on("tokenWillExpire", () => this.refreshToken())
      device.on("error", (e) => {
        this.logProgress(`device error ${e.code}`)
        showError("An unknown error occurred with your call. Try again.")
        warn("device error: ", e)
      })
    },
    hangup() {
      if (call) {
        if (get().callStep === CALL_STEP_VOICEMAIL) {
          this.logProgress("end voicemail pressed")
          call.sendDigits("*")
        } else {
          this.logProgress("hang up")
          call.disconnect()
        }
      } else {
        warn("Call NOT in progress, that's okay. Skipping hangup()")
      }
    },
    async call(cheat = false) {
      if (!call) {
        this.logProgress(`making call${cheat ? " (cheating)" : ""}`)
        call = await device.connect({ params: { assignmentId, cheat: cheat } })

        // Fake initial state until we hear otherwise from server
        update({ callInProgress: true, state: CALL_STEP_INITIAL })

        call.on("volume", (inputVolume, outputVolume) => {
          levels.set({
            mic: Math.min(inputVolume * 100 * levelsFuzzAmount, 100),
            speaker: Math.min(outputVolume * 100 * levelsFuzzAmount, 100)
          })
        })
        call.on("disconnect", () => {
          this.logProgress("call disconnect")
          update({ callInProgress: false })
          levels.set({ mic: 0, speaker: 0 })
          // If we're disconnected during the voicemail or done step, consider the assignment done (backend will too)
          if ([CALL_STEP_CALL, CALL_STEP_VOICEMAIL].includes(get().callStep)) {
            update({ callStep: CALL_STEP_DONE })
          }
          call = null
        })
        call.on("messageReceived", (data) => {
          const {
            content: { callStep, countdown, wordsHeard }
          } = data
          log(`Got message from twilio`, { callStep, countdown, wordsHeard })
          const hasCountdown = typeof countdown === "number" || null
          const normalizedCountdown = hasCountdown && dayjs().add(countdown, "second")
          this.logProgress(
            `call step: ${callStep}${hasCountdown ? ` [countdown=${countdown}]` : ""}${wordsHeard ? ` [wordsHeard=${wordsHeard}]` : ""}`
          )
          if (callStep) {
            update({ callStep, countdown: normalizedCountdown, wordsHeard })
          } else {
            warn("Got unknown user message from twilio", data)
          }
        })
        call.on("error", (e) => {
          if ([31401, 31402, 31208].includes(e.code)) {
            this.logProgress(`call audio error - mic may not be allowed: ${e.code}`)
            showError(
              "There was a problem with your audio. Are you sure your microphone is working and enabled? Are you sure the web browser has permission to use your microphone? If the problem persists, try another web browser next time. We recommend Chrome or Firefox."
            )
          } else {
            this.logProgress(`call error: ${e.code}`)
            showError("An unknown error occurred with your call. Try again.")
            warn("Unexpected call error:", e)
          }
        })
      } else {
        this.logProgress("attempting to make call, but call in progress")
        warn("Call already in progress! Can't call()")
      }
    },
    logProgress(progress) {
      if (!isPreview) {
        ;(async () => {
          if (assignmentId) {
            const { success } = await post("progress", { progress })
            if (!success) {
              warn(`Failed to log progress: ${progress}`)
            }
          } else {
            warn(`No assignmentId, can't log progress!`)
          }
        })()
      }
    },
    async updateName(name, gender) {
      name = name.trim()
      const { success } = await post("name", { name, gender })
      if (success) {
        this.logProgress(`name change: ${name}/${gender}`)
        update({ name, gender })
      } else {
        warn("Error updating name!")
      }
    },
    async finalize(data) {
      const { success, accepted, approvalCode, feedback, callDurationSeconds } = await post("finalize", data)
      if (success && accepted) {
        this.logProgress("finalize success")
        update({ approvalCode, feedback, callDurationSeconds })
        return true
      } else {
        this.logProgress("finalize error")
        return false
      }
    },
    setFailure(failure) {
      if (failure) {
        this.logProgress(`failure: ${failure}`)
      }
      update({ failure })
    }
  }
}

export const state = createState()
