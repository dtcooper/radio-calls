import { post } from "$lib/utils"
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
    failure: "",
    gender: "",
    isStaff: false,
    micLevel: 0,
    name: "",
    nameMaxLength: 0,
    ready: false,
    speakerLevel: 0,
    topic: ""
  })

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
        const { success, ...data } = await post("hit/handshake", { assignmentId, hitId, workerId, isPreview })
        if (!success) {
          fatalError(`Couldn't initialize! ${data.error}`)
          return
        }

        const { isStaff, ...rest } = data

        if (!isStaff) {
          debugMode.set(false)
        }

        update({ ready: true, isStaff, ...rest })
      }
    },
    async updateName(name, gender) {
      const { success } = await post("hit/name", { name, gender })
      if (!success) {
        console.warn("Error updating name")
      }
    }
  }
}

export const state = createState()
