export async function requestJSON(url, options = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), options.timeout || 120000);
  try {
    const response = await fetch(url, {...options, credentials: "same-origin", signal: controller.signal,
      headers: {"Content-Type": "application/json", ...options.headers}});
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = new Error(typeof data.detail === "string" ? data.detail : "Check the entered values and try again.");
      error.status = response.status; throw error;
    }
    return data;
  } catch (error) {
    if (error.status) throw error;
    throw new Error("Couldn’t connect. Please try again.");
  } finally { clearTimeout(timer); }
}
