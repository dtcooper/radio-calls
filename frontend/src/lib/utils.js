export const post = async (endpoint, data, debug = false) => {
  try {
    endpoint = `/api/hit/${endpoint}`
    if (debug) {
      console.log(`${endpoint}: call`, data)
    }
    const response = await fetch(endpoint, {
      method: "POST",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify(data)
    })
    const responseJson = await response.json()

    const { success, error } = responseJson
    if (!success) {
      console.warn(`Error from API (status code ${response.status}): ${error}`)
    }
    if (debug) {
      console.log(`${endpoint} response:`, responseJson)
    }
    return responseJson
  } catch (e) {
    console.error(`Error with fetch to ${endpoint}:`, e)
    return { success: false, error: "Server sent malformed response" }
  }
}

export const title = (s) =>
  s
    .split(" ")
    .map((w) => `${w.charAt(0).toUpperCase()}${w.substring(1)}`)
    .join(" ")
