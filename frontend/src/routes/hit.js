import { post as _post } from "$lib/utils"
import { Device } from "@twilio/voice-sdk"
import { persisted } from "svelte-persisted-store"
import { get as _get, derived, readonly, writable } from "svelte/store"

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

// Taken from models.py -- make sure they match
export const STAGE_INITIAL = "initial"
export const STAGE_VERIFIED = "verified"
export const STAGE_HOLD = "hold"
export const STAGE_CALL = "call"
export const STAGE_VOICEMAIL = "voicemail"
export const STAGE_DONE = "done"

export const isPreview = assignmentId === "ASSIGNMENT_ID_NOT_AVAILABLE"
export const debugMode = persisted("debug-mode", false)

const isDebug = () => _get(debugMode)

// Every endpoint takes the assignment ID
const post = (endpoint, data) => _post(endpoint, { assignmentId, ...data }, isDebug())

// Separate store for levels because this gets written to a lot
const levelsFuzzAmount = 1.25
const levels = writable({ speaker: 0, mic: 0 })
const readonlyLevels = readonly(levels)
export { readonlyLevels as levels }

const createState = () => {
  const { subscribe, update: _update } = writable({
    approvalCode: "invalid-approval-code",
    assignmentId: "",
    callInProgress: false,
    countdown: null,
    estimatedBeforeVerifiedDuration: null,
    failure: "",
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
    stage: STAGE_INITIAL,
    submitUrl: "",
    topic: "",
    wordsHeard: "",
    workerId: null
  })

  const update = (data) => _update(($state) => ({ ...$state, ...data }))
  const error = (msg) => update({ failure: msg })
  const fatalError = (msg) => update({ failure: msg, ready: false })

  setInterval(() => update({ now: dayjs() }), 250) // Up-to-date ish dayjs object for intervals
  const { subscribe: subscribeDerived } = derived({ subscribe }, ($state) => {
    let countdownDuration = null
    if ($state.countdown) {
      countdownDuration = dayjs.duration(Math.max($state.countdown.diff($state.now), 0))
    }

    const done = $state.stage === STAGE_DONE || ($state.stage === STAGE_VOICEMAIL && !$state.callInProgress)
    const canHangUp =
      $state.callInProgress &&
      (isDebug() ||
        $state.stage === STAGE_VOICEMAIL ||
        ($state.stage == STAGE_CALL && $state.now.isAfter($state.countdown)))

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
        const { success, ...data } = await post(url, { hitId, workerId, dbId, isPreview })
        if (!success) {
          fatalError(`Couldn't initialize! ${data.error}`)
          return
        }

        const { isStaff, token, ...rest } = data

        if (isStaff) {
          // In case we're staff, these may have been sent back by server if unspecified
          ;({ assignmentId, hitId, workerId } = data)
          if (!hitId) {
            console.warn("hitId was returned as null. This assignment doesn't appear to be actually hosted on Amazon.")
          }
        } else {
          debugMode.set(false)
        }

        if (!isPreview) {
          this.createDevice(token)
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

        if (isDebug()) {
          console.log("initial state:", get())
        }
      }
    },
    async refreshToken() {
      const { success, token } = await post("token")
      if (success) {
        device.updateToken(token)
      }
    },
    createDevice(token) {
      device = new Device(token, { closeProtection: true })
      device.on("tokenWillExpire", () => this.refreshToken())
      device.on("error", (e) => {
        error("An unknown error occurred with your call. Try again.")
        if (isDebug()) {
          console.warn("device error: ", e)
        }
      })
    },
    hangup() {
      if (call) {
        if (get().stage === STAGE_VOICEMAIL) {
          call.sendDigits("*")
        } else {
          call.disconnect()
        }
      } else if (isDebug()) {
        console.warn("Call NOT in progress, skipping hangup()")
      }
    },
    async call(cheat = false) {
      if (!call) {
        call = await device.connect({ params: { assignmentId, cheat: cheat } })

        // Fake initial state until we hear otherwise from server
        update({ callInProgress: true, state: STAGE_INITIAL })

        call.on("volume", (inputVolume, outputVolume) => {
          levels.set({
            mic: Math.min(inputVolume * 100 * levelsFuzzAmount, 100),
            speaker: Math.min(outputVolume * 100 * levelsFuzzAmount, 100)
          })
        })
        call.on("disconnect", () => {
          update({ callInProgress: false })
          levels.set({ mic: 0, speaker: 0 })
          // If we're disconnected during the voicemail or call stage, consider the assignment done (backend will too)
          if ([STAGE_CALL, STAGE_VOICEMAIL].includes(get().stage)) {
            update({ stage: STAGE_DONE })
          }
          call = null
        })
        call.on("messageReceived", (data) => {
          const {
            content: { stage, countdown, wordsHeard }
          } = data
          if (isDebug()) {
            console.log(`Got message from twilio`, data)
          }
          if (stage) {
            update({ stage, countdown: countdown && dayjs().add(countdown, "second"), wordsHeard })
          } else {
            console.warn("Got unknown user message from twilio", data)
          }
        })
        call.on("error", (e) => {
          if ([31401, 31208].includes(e.code)) {
            error("There was a problem with your audio. Are you sure your microphone is enabled?", e)
          } else {
            error("An unknown error occured with your call. Try again.")
            if (isDebug()) {
              console.warn("call error:", e)
            }
          }
        })
      } else {
        console.warn("Call already in progress! Can't call()")
      }
    },
    async updateName(name, gender) {
      const { success } = await post("name", { name, gender })
      if (success) {
        update({ name, gender })
      } else {
        console.warn("Error updating name!")
      }
    },
    async finalize() {
      const { success, accepted, approvalCode } = await post("finalize")
      if (success && accepted) {
        update({ approvalCode })
        return true
      }
      return false
    },
    setFailure(failure) {
      update({ failure })
    }
  }
}

export const state = createState()
