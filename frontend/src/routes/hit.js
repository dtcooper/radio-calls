import { post as _post } from "$lib/utils"
import { Device } from "@twilio/voice-sdk"
import { persisted } from "svelte-persisted-store"
import { get as _get, derived, writable } from "svelte/store"

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

const post = (endpoint, data) => _post(endpoint, data, isDebug())

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
    isStaff: false,
    isProd: true,
    leaveVoicemailAfterDuration: null,
    micLevel: 0,
    minCallDuration: null,
    name: "",
    nameMaxLength: 0,
    now: dayjs(),
    ready: false,
    showHost: "",
    speakerLevel: 0,
    stage: STAGE_INITIAL,
    submitUrl: "",
    topic: "",
    workerId: null
  })

  const update = (data) => _update(($state) => ({ ...$state, ...data }))
  const fatalError = (msg, e) => {
    if (e && isDebug()) {
      msg += ` [Error: ${e}]`
    }
    update({ failure: msg })
  }

  setInterval(() => update({ now: dayjs() }), 500)
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
        const { success, ...data } = await post(url, { assignmentId, hitId, workerId, dbId, isPreview })
        if (!success) {
          fatalError(`Couldn't initialize! ${data.error}`)
          return
        }

        const { isStaff, token, ...rest } = data

        if (isStaff) {
          // In case we're staff, these may have been sent back by server if unspecified
          ;({ assignmentId, hitId, workerId } = data)
          if (!hitId) {
            console.warn("hitId was returned as null. This assignment doesn't appear to be hosted by Amazon.")
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
          submitUrl: turkSubmitTo && `${turkSubmitTo}mturk/externalSubmit`,
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
        console.warn("An twilio error has occurred: ", e)
        // TODO: Use a toast
        update({ failure: e.message })
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
        try {
          call = await device.connect({ params: { assignmentId, cheat: cheat } })
        } catch (e) {
          console.error("Error placing call", e)
          return
        }

        // Fake initial state until we hear otherwise from server
        update({ callInProgress: true, state: STAGE_INITIAL })

        call.on("volume", (inputVolume, outputVolume) => {
          const micLevel = Math.min(inputVolume * 100 * 1.25, 100)
          const speakerLevel = Math.min(outputVolume * 100 * 1.25, 100)
          update({ micLevel, speakerLevel })
        })
        call.on("disconnect", () => {
          update({ micLevel: 0, speakerLevel: 0, callInProgress: false })
          // If we're disconnected during the voicemail or call stage, consider the assignment done (backend will too)
          if ([STAGE_CALL, STAGE_VOICEMAIL].includes(get().stage)) {
            update({ stage: STAGE_DONE })
          }
          call = null
        })
        call.on("messageReceived", (data) => {
          const {
            content: { stage, countdown }
          } = data
          if (isDebug()) {
            console.log(`Got message from twilio stage=${stage}, countdown=${countdown}`)
          }
          if (stage) {
            update({ stage, countdown: countdown && dayjs().add(countdown, "second") })
          } else {
            console.warn("Got unknown user message from twilio", data)
          }
        })
        // TODO: Use a toast on error
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
    }
  }
}

export const state = createState()
