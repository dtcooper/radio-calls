export const post = async (endpoint, data) => {
  try {
    let response
    if (data instanceof FormData) {
      response = await fetch(`/api/${endpoint}`, {
        method: "POST",
        headers: { Accept: "application/json" },
        body: data
      })
    } else {
      response = await fetch(`/api/${endpoint}`, {
        method: "POST",
        headers: { Accept: "application/json", "Content-Type": "application/json" },
        body: JSON.stringify(data)
      })
    }
    if (response.status != 200) {
      console.error(`Fetch to ${endpoint} received response code: ${response.status}`)
      let error = "Server returned an unexpected response"
      if (response.status >= 400 && response.status < 500) {
        const { detail } = await response.json()
        error = detail
      }
      return { success: false, data: error }
    }
    return { success: true, data: await response.json() }
  } catch (e) {
    console.error(`Error with fetch to ${endpoint}:`, e)
    return { success: false, data: "Server returned an unexpected response" }
  }
}
