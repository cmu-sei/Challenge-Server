/*
 * Challenge Sever
 * Copyright 2024 Carnegie Mellon University.
 * NO WARRANTY. THIS CARNEGIE MELLON UNIVERSITY AND SOFTWARE ENGINEERING INSTITUTE MATERIAL IS FURNISHED ON AN "AS-IS" BASIS. CARNEGIE MELLON UNIVERSITY MAKES NO WARRANTIES OF ANY KIND, EITHER EXPRESSED OR IMPLIED, AS TO ANY MATTER INCLUDING, BUT NOT LIMITED TO, WARRANTY OF FITNESS FOR PURPOSE OR MERCHANTABILITY, EXCLUSIVITY, OR RESULTS OBTAINED FROM USE OF THE MATERIAL. CARNEGIE MELLON UNIVERSITY DOES NOT MAKE ANY WARRANTY OF ANY KIND WITH RESPECT TO FREEDOM FROM PATENT, TRADEMARK, OR COPYRIGHT INFRINGEMENT.
 * Licensed under a MIT (SEI)-style license, please see license.txt or contact permission@sei.cmu.edu for full terms.
 * [DISTRIBUTION STATEMENT A] This material has been approved for public release and unlimited distribution.  Please see Copyright notice for non-US Government use and distribution.
 * DM24-0645
 */

/*
 * Polls /challenge/update immediately on load, then every 5s,
 */

document.addEventListener("DOMContentLoaded", () => {
    const POLL_INTERVAL    = 5000;
    const RESULTS_DIV_ID   = "results";
    const FIELDSET_WIDTH   = "70%";

    const resultsDiv = document.getElementById(RESULTS_DIV_ID);
    if (!resultsDiv) return;

    async function fetchAndRender() {
      try {
        const resp = await fetch("/challenge/update");
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const res = await resp.json();

        // Clear out old
        resultsDiv.innerHTML = "";

        // Handle errors / “no grades”
        if (res.fatal_error) {
          const err = document.createElement("div");
          err.className = "error";
          err.innerHTML = `
            <h2>There was an error grading your challenge</h2>
            <p>The grading error has been logged. If it persists, please contact support.</p>
          `;
          resultsDiv.appendChild(err);
          return;
        }
        if (res.cron_results == null && res.manual_results == null) {
          const p = document.createElement("p");
          p.id = "no-grade";
          p.textContent = "No grades yet. Grades will show after grading occurs.";
          resultsDiv.appendChild(p);
          return;
        }

        const table = document.createElement("table");
        table.className = "res-table";

        const thead = document.createElement("thead");
        thead.className = "res-thead";
        const headRow = document.createElement("tr");
        ["Task", "Status", "Result"].forEach((txt, i) => {
          const th = document.createElement("th");
          th.className = i === 0 ? "home_table_page" : "home_table_func";
          th.textContent = txt;
          headRow.appendChild(th);
        });
        thead.appendChild(headRow);
        table.appendChild(thead);

        const tbody = document.createElement("tbody");
        function appendRows(obj, type) {
          if (!obj) return;
          Object.keys(obj)
            .sort((a, b) => {
              const na = parseInt(a.match(/\d+/) || 0, 10),
                    nb = parseInt(b.match(/\d+/) || 0, 10);
              return na - nb;
            })
            .forEach((key) => {
              const tr = document.createElement("tr");
              tr.className = "bodypost";

              // Task
              const td1 = document.createElement("td");
              td1.className = "home_table_page";
              td1.textContent = res.grading_parts[key].text;
              tr.appendChild(td1);

              // Status
              const td2 = document.createElement("td");
              td2.className = "home_table_func";
              td2.textContent = obj[key];
              tr.appendChild(td2);

              // Token
              const td3 = document.createElement("td");
              td3.className = "home_table_func";
              td3.textContent = (res.tokens[type] || {})[key] || "";
              tr.appendChild(td3);

              tbody.appendChild(tr);
            });
        }
        if (res.manual_enabled) appendRows(res.manual_results, "manual");
        if (res.cron_enabled)   appendRows(res.cron_results,  "cron");
        table.appendChild(tbody);

        // last-submission info
        const tfoot = document.createElement("tfoot");
        const footRow = document.createElement("tr");
        const footCell = document.createElement("th");
        footCell.colSpan = 3;
        footCell.className = "resspan";
        if (res.manual_enabled && res.manual_submit_time) {
          footCell.textContent = `Last manual submission: ${res.manual_submit_time}`;
        } else if (res.cron_enabled && res.cron_submit_time) {
          footCell.textContent = `Auto-grading last triggered at: ${res.cron_submit_time}`;
        }
        footRow.appendChild(footCell);
        tfoot.appendChild(footRow);
        table.appendChild(tfoot);

        // “Re-Grade” button
        const regradeBtn = document.createElement("button");
        regradeBtn.type = "button";
        regradeBtn.className = "btn btn-default";
        regradeBtn.textContent = "Re-Grade Tasks";
        regradeBtn.addEventListener("click", () => {
          window.location.href = "/challenge/tasks";
        });

        const form = document.createElement("form");
        const fieldset = document.createElement("fieldset");
        fieldset.style.width = FIELDSET_WIDTH;
        fieldset.appendChild(table);
        fieldset.appendChild(regradeBtn);
        form.appendChild(fieldset);
        resultsDiv.appendChild(form);

      } catch (e) {
        console.error("Fetch error:", e);
      }
    }

    // fire once now, then every 5s
    fetchAndRender();
    setInterval(fetchAndRender, POLL_INTERVAL);
  });
