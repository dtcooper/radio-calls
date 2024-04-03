import { post as _post } from "$lib/utils"
import { Device } from "@twilio/voice-sdk"
import { persisted } from "svelte-persisted-store"
import { get as _get, writable } from "svelte/store"

const params = new URLSearchParams(window.location.search)
let assignmentId = params.get("assignmentId")
let hitId = params.get("hitId")
let workerId = params.get("workerId")
let dbId = params.get("dbId")
export const isPreview = assignmentId === "ASSIGNMENT_ID_NOT_AVAILABLE"
export const debugMode = persisted("debug-mode", false)
const isDebug = () => _get(debugMode)

const post = (endpoint, data) => _post(endpoint, data, isDebug())

const createState = () => {
  const { subscribe, update: _update } = writable({
    failure: "",
    gender: "",
    isStaff: false,
    micLevel: 0,
    name: "",
    nameMaxLength: 0,
    ready: false,
    speakerLevel: 0,
    topic: "",
    showHost: "",
    callInProgress: false,
    disconnect: null
  })

  const update = (data) => _update(($state) => ({ ...$state, ...data }))
  const get = () => _get({ subscribe })
  const fatalError = (msg, e) => {
    if (e && isDebug()) {
      msg += ` [Error: ${e}]`
    }
    update({ failure: msg })
  }

  /** @type {Device} */
  let device

  /** @type {import("@twilio/voice-sdk").Call}} */
  let call = null

  return {
    subscribe,
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

        update({ ready: true, isStaff, ...rest })
      }
    },
    async refreshToken() {
      const { success, token } = await post("token")
      if (success) {
        device.updateToken(token)
      }
    },
    createDevice(token) {
      device = new Device(token)
      device.on("tokenWillExpire", () => this.refreshToken())
      device.on("error", (e) => {
        console.warn("An twilio error has occurred: ", e)
        // TODO: Use a toast
        update({ failure: e.message })
      })
    },
    hangup() {
      if (call) {
        call.disconnect()
      } else {
        console.warn("Call NOT in progress, can't hangup()")
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

        update({ callInProgress: true })

        call.on("volume", (inputVolume, outputVolume) => {
          const micLevel = Math.min(inputVolume * 100 * 1.25, 100)
          const speakerLevel = Math.min(outputVolume * 100 * 1.25, 100)
          update({ micLevel, speakerLevel })
        })
        call.on("disconnect", () => {
          update({ micLevel: 0, speakerLevel: 0, callInProgress: false })
          call = null
        })
        call.on("messageReceived", (message) => {
          console.log("GOT MESSAGE", message)
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
    }
  }
}

export const state = createState()
