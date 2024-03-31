import { Peer } from "peerjs"
import { noop } from "svelte/internal"

const params = new URLSearchParams(window.location.search)

export const post = async (endpoint, data) => {
  try {
    const options = { method: "POST", headers: { Accept: "application/json" } }
    if (data instanceof FormData) {
      options.body = data
    } else {
      options.body = JSON.stringify(data)
      options.headers["Content-Type"] = "application/json"
    }

    const response = await fetch(`/api/${endpoint}`, options)

    const { success, ...rest } = await response.json()
    if (!success) {
      console.warn(`Error from API (status code ${response.status}): ${rest.error}`)
    }
    return { success, ...rest }
  } catch (e) {
    console.error(`Error with fetch to ${endpoint}:`, e)
    return { success: false, error: "Server sent malformed response" }
  }
}

const average = (values) => {
  return values && values.length ? values.reduce((t, v) => t + v) / values.length : 0
}

export const createVolumeAnalyser = (context, callback) => {
  const analyser = context.createAnalyser()
  analyser.fftSize = 32
  analyser.smoothingTimeConstant = 0.85
  const bufferLength = analyser.frequencyBinCount
  const buffer = new Uint8Array(bufferLength)

  const listen = () => {
    analyser.getByteFrequencyData(buffer)
    callback(Math.min((average(buffer) / 255) * 125, 100)) // Fudge it a bit
    requestAnimationFrame(listen)
  }
  requestAnimationFrame(listen)

  return analyser
}

export const getMicAndInitAudio = async () => {
  for (const action of ["play", "pause", "seekbackward", "seekforward", "previoustrack", "nexttrack"]) {
    navigator.mediaSession.setActionHandler(action, noop)
  }

  return await navigator.mediaDevices.getUserMedia({
    audio: { echoCancellation: true, autoGainControl: true },
    video: false
  })
}

const fatalPeerErrors = [
  "browser-incompatible",
  "invalid-id",
  "invalid-key",
  "ssl-unavailable",
  "server-error",
  "socket-error",
  "socket-closed",
  "unavailable-id"
]

export const initializePeer = (id, key) => {
  const host = params.get("peerHost") || window.location.hostname
  const port = params.has("peerPort") ? +params.get("peerPort") : 9000
  const secure = params.has("peerSecure") ? params.get("peerSecure") : window.location.protocol === "https:"
  const debug = params.has("peerDebug") ? +params.get("peerDebug") : host === "localhost" ? 2 : 0

  return new Promise((resolve, reject) => {
    const peer = new Peer(id, { host, port, secure, debug, key })
    peer.on("open", () => {
      console.log(`Peer ${id} connection initialized`)
      peer.off("open")
      peer.off("error")
      resolve(peer)
    })
    peer.on("error", (e) => {
      if (fatalPeerErrors.includes(e.type)) {
        reject(e.type)
      }
    })
  })
}
