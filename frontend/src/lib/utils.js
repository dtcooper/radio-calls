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
    console.log(endpoint, { success, ...rest })
    return { success, ...rest }
  } catch (e) {
    console.error(`Error with fetch to ${endpoint}:`, e)
    return { success: false, error: "Server sent malformed response" }
  }
}

const average = (values) => {
  return values && values.length ? values.reduce((t, v) => t + v) / values.length : 0
}

export const runVolumeAnalyser = (source, callback) => {
  const analyser = source.context.createAnalyser()
  analyser.fftSize = 32
  analyser.smoothingTimeConstant = 0.85
  const bufferLength = analyser.frequencyBinCount
  const buffer = new Uint8Array(bufferLength)

  source.connect(analyser)

  const listen = () => {
    analyser.getByteFrequencyData(buffer)
    callback(Math.min((average(buffer) / 255) * 125, 100)) // Fudge it a bit
    requestAnimationFrame(listen)
  }
  requestAnimationFrame(listen)
}
