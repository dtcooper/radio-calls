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
    console.log({ success, ...rest })
    return { success, ...rest }
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
