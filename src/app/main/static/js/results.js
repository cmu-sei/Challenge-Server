/*
 * Challenge Sever
 * Copyright 2024 Carnegie Mellon University.
 * NO WARRANTY. THIS CARNEGIE MELLON UNIVERSITY AND SOFTWARE ENGINEERING INSTITUTE MATERIAL IS FURNISHED ON AN "AS-IS" BASIS. CARNEGIE MELLON UNIVERSITY MAKES NO WARRANTIES OF ANY KIND, EITHER EXPRESSED OR IMPLIED, AS TO ANY MATTER INCLUDING, BUT NOT LIMITED TO, WARRANTY OF FITNESS FOR PURPOSE OR MERCHANTABILITY, EXCLUSIVITY, OR RESULTS OBTAINED FROM USE OF THE MATERIAL. CARNEGIE MELLON UNIVERSITY DOES NOT MAKE ANY WARRANTY OF ANY KIND WITH RESPECT TO FREEDOM FROM PATENT, TRADEMARK, OR COPYRIGHT INFRINGEMENT.
 * Licensed under a MIT (SEI)-style license, please see license.txt or contact permission@sei.cmu.edu for full terms.
 * [DISTRIBUTION STATEMENT A] This material has been approved for public release and unlimited distribution.  Please see Copyright notice for non-US Government use and distribution.
 * DM24-0645
 */

(function () {
    x = setInterval(function () {
        var xhr = new XMLHttpRequest();
        xhr.open("GET", "/challenge/update", true);
        xhr.onerror = err => console.log('error: ' + err.message);
        xhr.onload = function() {
            if (this.readyState == 4 && this.status == 200) {
                res = JSON.parse(this.responseText);

                var data = document.getElementById('results');

                if (res.fatal_error === true) {
                    err_check = document.getElementById('err');
                    if (data.contains(err_check)) {
                        data.removeChild(err_check)
                    }
                    var err1 = document.createElement('h2');
                    err1.id ='err'
                    err1.textContent = 'There was an error grading your challenge';
                    var err2 = document.createElement('p');
                    err2.textContent = 'The grading error has been logged. If the error is not resolved by re-grading, please contact support.';
                    err1.appendChild(err2);
                    data.appendChild(err1);

                }
                else if (res.cron_results === null && res.manual_results === null) {
                    child_check = document.getElementById('top-level');
                    if (data.contains(child_check)) {
                        data.removeChild(child_check)
                    }
                    if (data.children[0] === undefined) {
                        var child1 = document.createElement('p');
                        child1.id = 'no-grade'
                        child1.textContent = 'No grades yet. Grades will show after grading occurs.';
                        data.appendChild(child1);
                    }
                    else if (!data.children[0].textContent.includes('No grading')){
                        var child1 = document.createElement('p');
                        child1.textContent = 'No grades yet. Grades will show after grading occurs.';
                        data.appendChild(child1);
                    }
                }
                else {
                    /* checking if it is already setup.*/
                    child_check = document.getElementById('top-level');
                    if (data.contains(child_check)) {
                        data.removeChild(child_check)
                    }
                    old_msg = document.getElementById('no-grade');
                    if (data.contains(old_msg)) {
                        data.removeChild(old_msg)
                    }
                    var child1 = document.createElement('form');
                    child1.id = 'top-level';
                    var child2 = document.createElement('fieldset');
                    var child3 = document.createElement('legend');
                    child3.align = 'center';
                    child3.textContent = 'Grading Results'
                    var table = document.createElement('table');
                    table.className = 'res-table';
                    /* create table header */
                    var thead = document.createElement('thead');
                    thead.className = 'res-thead';
                    var child6 = document.createElement('th');
                    var child7 = document.createElement('th');
                    var child8 = document.createElement('th');
                    child6.className = 'reslist1';
                    child7.className = 'reslist2';
                    child8.className = 'reslist2';
                    child6.textContent = 'Task';
                    child7.textContent = 'Status';
                    child8.textContent = 'Result';
                    thead.appendChild(child6);
                    thead.appendChild(child7);
                    thead.appendChild(child8);
                    table.appendChild(thead);
                    /* create table contents */
                    if (res.manual_enabled == true) {
                        if (res.manual_results !== null ) {
                            msg_chk = document.getElementById('gradenotrun');
                            if (table.contains(msg_chk)) {
                                table.removeChild(msg_chk)
                            }
                            let manual_keys = Object.keys(res.manual_results);
                            manual_keys.sort((a, b) => {
                                let numA = parseInt(a.match(/\d+/));
                                let numB = parseInt(b.match(/\d+/));
                                return numA - numB;
                            });
                            for (let mk of manual_keys) {
                                var tr = document.createElement('tr');
                                tr.className = 'bodypost';
                                td1 = document.createElement('td');
                                td2 = document.createElement('td');
                                td3 = document.createElement('td');
                                td1.className = 'reslist1';
                                td2.className = 'reslist2';
                                td3.className = 'reslist2';
                                var l1 = document.createElement('label')
                                var l2 = document.createElement('label')
                                var l3 = document.createElement('label')
                                l1.textContent = res.grading_parts[mk]['text'];
                                l2.textContent = res.manual_results[mk];
                                l3.textContent = res.tokens['manual'][mk];
                                td1.appendChild(l1);
                                td2.appendChild(l2);
                                td3.appendChild(l3);
                                tr.appendChild(td1);
                                tr.appendChild(td2);
                                tr.appendChild(td3);
                                table.appendChild(tr);
                            }
                            var tr2 = document.createElement('tr');
                            var th = document.createElement('th');
                            th.colSpan = "3";
                            th.className = 'resspan';
                            th.textContent = "Last Submission of manual tasks: " + res.manual_submit_time;
                            tr2.appendChild(th);
                            table.appendChild(tr2);
                        }
                        else {
                            var tr3 = document.createElement('tr');
                            var th = document.createElement('th');
                            th.colSpan = "3";
                            th.className = 'resspan';
                            th.textContent = "No manual grades yet.";
                            tr3.appendChild(th);
                            table.appendChild(tr3);
                        }
                    }
                    if (res.cron_enabled == true) {
                        if (res.cron_results !== null ) {
                            msg_chk = document.getElementById('gradenotrun');
                            if (table.contains(msg_chk)) {
                                table.removeChild(msg_chk)
                            }
                            let cron_keys = Object.keys(res.cron_results);
                            cron_keys.sort((a, b) => {
                                let numA = parseInt(a.match(/\d+/));
                                let numB = parseInt(b.match(/\d+/));
                                return numA - numB;
                            });
                            for (let ck of cron_keys) {
                                var tr4 = document.createElement('tr');
                                tr4.className = 'bodypost';
                                td1 = document.createElement('td');
                                td2 = document.createElement('td');
                                td3 = document.createElement('td');
                                td1.className = 'reslist1';
                                td2.className = 'reslist2';
                                td3.className = 'reslist2';
                                var l1 = document.createElement('label')
                                var l2 = document.createElement('label')
                                var l3 = document.createElement('label')
                                l1.textContent = res.grading_parts[ck]['text'];
                                l2.textContent = res.cron_results[ck];
                                l3.textContent = res.tokens['cron'][ck];
                                td1.appendChild(l1);
                                td2.appendChild(l2);
                                td3.appendChild(l3);
                                tr4.appendChild(td1);
                                tr4.appendChild(td2);
                                tr4.appendChild(td3);
                                table.appendChild(tr4);
                            }
                            var tr5 = document.createElement('tr');
                            var th = document.createElement('th');
                            th.colSpan = "3";
                            th.className = 'resspan';
                            th.textContent = "Auto-grading last triggered at: " + res.cron_submit_time;
                            tr5.appendChild(th);
                            table.appendChild(tr5);
                        }
                        else {
                            var tr6 = document.createElement('tr');
                            tr.id = "gradenotrun"
                            var th = document.createElement('th');
                            th.colSpan = "3";
                            th.className = 'resspan';
                            th.textContent = "No cron grades yet.";
                            tr6.appendChild(th);
                            table.appendChild(tr6);
                        }
                    }
                    var regrade = document.createElement('form');
                    regrade.action = "/challenge/tasks";
                    regrade.method = 'GET';
                    var link = document.createElement('a');
                    link.id = 'regrade';
                    var btn = document.createElement('button');
                    btn.class = 'btn btn-default';
                    btn.textContent = "Re-Grade Tasks";
                    link.appendChild(btn);
                    regrade.appendChild(link)
                    child2.appendChild(table);
                    child2.appendChild(regrade);
                    child1.appendChild(child2);
                    data.appendChild(child1);

                }
            }
        }
        xhr.send();
    },1000);
})();
