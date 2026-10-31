(function () {
  "use strict";
  const form = document.getElementById("run");
  const button = document.getElementById("submit");
  const job = document.getElementById("job");
  const output = document.getElementById("output");
  form.addEventListener("submit", async function (event) {
    event.preventDefault();
    output.hidden = true;
    button.disabled = true;
    job.textContent = "Executing the admitted original synthetic renderer.";
    try {
      const capResponse = await fetch("/v1/capabilities", {cache:"no-store"});
      if (!capResponse.ok) throw Error("Capability read failed");
      const capabilities = await capResponse.json();
      if (capabilities.scope !== "public-synthetic" ||
          capabilities.release !== "HELD_R009_NOT_RUN_NOT_ADMITTED") {
        throw Error("Unexpected release scope");
      }
      const response = await fetch("/v1/jobs", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
          schema:"scp.native-job-request.v1",
          job_id:"w7a-forward-24",
          revision:capabilities.revision,
          source_class:"public-synthetic"
        })
      });
      const result = await response.json();
      if (!response.ok) throw Error(result.code || "Native job failed");
      if (result.human_behavior !== "FAIL_ABSTRACT_LIMBS_ONLY" ||
          result.release !== "HELD_R009_NOT_RUN_NOT_ADMITTED") {
        throw Error("Scientific first failure or release hold not preserved");
      }
      document.getElementById("front").src = "/v1/jobs/w7a-forward-24/media/OriginalFront";
      document.getElementById("oblique").src = "/v1/jobs/w7a-forward-24/media/OriginalOblique";
      output.hidden = false;
      job.textContent = "Original two-view video created. Human behavior FAIL, anatomy UNKNOWN, release HELD.";
    } catch (error) {
      job.textContent = "Run not accepted or unsuccessful: " + error.message;
    } finally {
      button.disabled = false;
    }
  });
}());
