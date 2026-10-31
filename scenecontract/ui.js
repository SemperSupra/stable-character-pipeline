document.getElementById("validate").addEventListener("submit", async function (event) {
  event.preventDefault();
  const output = document.getElementById("result");
  const source = document.getElementById("scene").value;
  try {
    const response = await fetch("/v1/scenes/validate", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: source
    });
    const decision = await response.json();
    output.textContent = decision.status + ": " + decision.code + " (HTTP " + response.status + ")";
  } catch (error) {
    output.textContent = "ERROR: request failed";
  }
});
