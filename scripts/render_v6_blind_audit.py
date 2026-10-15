"""Render the reference-free v6 audit packet as a standalone local HTML form."""
import hashlib
import html
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DIRECTORY=ROOT/'results/private/v6_blind_semantic_audit'
PACKET=DIRECTORY/'audit_packet.json'
OUTPUT=DIRECTORY/'reviewer_packet.html'


def main():
    if OUTPUT.exists():raise ValueError('reviewer_html_already_exists')
    packet=json.loads(PACKET.read_text());packet_sha=hashlib.sha256(PACKET.read_bytes()).hexdigest()
    embedded=json.dumps(packet,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
    page='''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Blind OR semantic audit</title>
<style>
body{margin:0;background:#f4f6f8;color:#17202a;font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
header{position:sticky;top:0;z-index:4;background:#132238;color:white;padding:14px 24px;display:flex;gap:18px;align-items:center;box-shadow:0 2px 8px #0003}
header strong{font-size:18px}header span{opacity:.85}.wrap{max-width:1180px;margin:24px auto;padding:0 18px}.notice,.item{background:white;border:1px solid #d9e0e7;border-radius:10px;padding:20px;margin-bottom:20px;box-shadow:0 2px 8px #22313f0d}
.notice{border-left:5px solid #2874a6}.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}.model{border:1px solid #d9e0e7;border-radius:8px;padding:12px;overflow:auto}.model h3{margin-top:0}.text{white-space:pre-wrap;background:#f8fafb;padding:14px;border-radius:7px}.contract{background:#fff8e6;border-left:4px solid #d68910;padding:10px;margin:8px 0;white-space:pre-wrap}table{border-collapse:collapse;width:100%;font-size:13px}th,td{border:1px solid #dfe6ec;padding:6px;text-align:left;vertical-align:top}th{background:#eef3f7}.questions{margin-top:16px;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.field{display:flex;flex-direction:column;gap:5px}.field.full{grid-column:1/-1}select,textarea,input{font:inherit;padding:8px;border:1px solid #aeb9c4;border-radius:6px}textarea{min-height:95px}button{border:0;border-radius:7px;padding:10px 15px;font-weight:650;cursor:pointer}.export{background:#1f7a4d;color:white}.clear{background:#dfe6ec}.badge{background:#e8f1fa;color:#174a73;padding:3px 8px;border-radius:99px;font-size:12px}@media(max-width:850px){.grid,.questions{grid-template-columns:1fr}}
</style></head><body>
<header><strong>Blind OR semantic audit</strong><span id="progress">0 / 0 complete</span><button class="export" onclick="exportAnswers()">Validate &amp; export sealed JSON</button><button class="clear" onclick="clearDraft()">Clear local draft</button></header>
<main class="wrap"><section class="notice"><h2>Reviewer rules</h2><ul id="rubric"></ul><p><b>Do not</b> consult published answers, evaluation files, or the private randomization key. Judge the public language and the complete formulations. Use <i>unclear</i> when the text or interface does not determine the answer.</p><label>Reviewer identifier <input id="reviewer" autocomplete="off" placeholder="Use your assigned reviewer ID"></label></section><div id="items"></div></main>
<script id="packet" type="application/json">__PACKET__</script><script>
const packet=JSON.parse(document.getElementById('packet').textContent);const packetSha='__SHA__';
const choices={contract_faithfulness:['','correct','incorrect','unclear'],preferred_complete_model:['','A','B','both','neither','unclear'],interface_sufficient:['','yes','no','unclear'],confidence:['','high','medium','low']};
const labels={contract_faithfulness:'Is the proposed semantic contract faithful?',preferred_complete_model:'Which complete model is preferable?',interface_sufficient:'Is the declared interface sufficient?',confidence:'Confidence'};
function esc(x){return String(x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function model(m){const vars=m.variables.map(v=>`<tr><td>${esc(v.id)}</td><td>${esc(v.meaning)}</td><td>${esc(v.unit)}</td><td>${esc(v.domain)}</td><td>${esc(v.lower)} … ${esc(v.upper)}</td></tr>`).join('');const rows=m.constraints.map(r=>`<tr><td>${esc(r.id)}</td><td><code>${esc(JSON.stringify(r.coefficients))}</code></td><td>${esc(r.sense)}</td><td>${esc(r.rhs)}</td></tr>`).join('');return `<h4>Variables</h4><table><tr><th>ID</th><th>Meaning</th><th>Unit</th><th>Domain</th><th>Bounds</th></tr>${vars}</table><h4>Constraints</h4><table><tr><th>ID</th><th>Coefficients</th><th>Sense</th><th>RHS</th></tr>${rows}</table><h4>Objective</h4><div><code>${esc(JSON.stringify(m.objective))}</code></div>`}
function restore(){try{return JSON.parse(localStorage.getItem('v6BlindAuditDraft')||'{}')}catch{return {}}}
const draft=restore();document.getElementById('reviewer').value=draft.reviewer_id||'';
document.getElementById('rubric').innerHTML=packet.instructions.rubric.map(x=>`<li>${esc(x)}</li>`).join('');
document.getElementById('items').innerHTML=packet.items.map((x,i)=>{const contracts=x.proposed_semantic_contracts.map(c=>`<div class="contract">${esc(JSON.stringify(c,null,2))}</div>`).join('');const fields=Object.keys(choices).map(k=>`<label class="field"><b>${esc(labels[k])}</b><select data-id="${esc(x.audit_id)}" data-field="${k}">${choices[k].map(v=>`<option value="${v}">${v||'Choose…'}</option>`).join('')}</select></label>`).join('');return `<section class="item"><h2>Item ${i+1} <span class="badge">${esc(x.audit_id)}</span></h2><h3>Public problem</h3><div class="text">${esc(x.public_input.text)}</div><h3>Proposed semantic contract(s)</h3>${contracts}<div class="grid"><div class="model"><h3>Candidate A</h3>${model(x.candidate_A)}</div><div class="model"><h3>Candidate B</h3>${model(x.candidate_B)}</div></div><div class="questions">${fields}<label class="field full"><b>Rationale with exact clause and algebra/domain reasoning</b><textarea data-id="${esc(x.audit_id)}" data-field="rationale"></textarea></label></div></section>`}).join('');
for(const el of document.querySelectorAll('[data-id]')){const old=(draft.answers||[]).find(x=>x.audit_id===el.dataset.id);if(old&&old[el.dataset.field])el.value=old[el.dataset.field];el.addEventListener('input',save)}document.getElementById('reviewer').addEventListener('input',save);
function collect(){return packet.items.map(x=>{const row={audit_id:x.audit_id};for(const el of document.querySelectorAll(`[data-id="${x.audit_id}"]`))row[el.dataset.field]=el.value.trim();return row})}
function save(){const answers=collect();localStorage.setItem('v6BlindAuditDraft',JSON.stringify({reviewer_id:document.getElementById('reviewer').value.trim(),answers}));const done=answers.filter(x=>Object.keys(choices).every(k=>x[k])&&x.rationale).length;document.getElementById('progress').textContent=`${done} / ${answers.length} complete`}
function exportAnswers(){const reviewer=document.getElementById('reviewer').value.trim(),answers=collect();if(!reviewer){alert('Enter the assigned reviewer identifier.');return}const incomplete=answers.filter(x=>!Object.keys(choices).every(k=>x[k])||!x.rationale);if(incomplete.length){alert(`${incomplete.length} item(s) are incomplete.`);return}const out={reviewer_id:reviewer,packet_sha256:packetSha,sealed:true,answers};const blob=new Blob([JSON.stringify(out,null,2)+'\\n'],{type:'application/json'}),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=`${reviewer}_v6_blind_review.json`;a.click();URL.revokeObjectURL(a.href)}
function clearDraft(){if(confirm('Clear this browser\'s local draft?')){localStorage.removeItem('v6BlindAuditDraft');location.reload()}}save();
</script></body></html>'''.replace('__PACKET__',embedded).replace('__SHA__',packet_sha)
    OUTPUT.write_text(page)
    print(json.dumps({'status':'rendered','items':len(packet['items']),'packet_sha256':packet_sha,
                      'html_sha256':hashlib.sha256(OUTPUT.read_bytes()).hexdigest()}))


if __name__=='__main__':main()
