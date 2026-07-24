<?php
// doubled.life authed view — four faithful index layouts (ESPN 2010 portal,
// Napster transfer-list, CNN zones, iTunes library), each rendering the live
// $subjects / $videos, recolored to the palette. Toggle persists in
// localStorage. Included by index.php inside the authed branch.
$hero = $subjects[0] ?? null;
$rest = array_slice($subjects, 1);
function dl_rows($subjects) { return $subjects; }
?>
<style>
  /* per-view scoping so the four skeuomorphic CSS sets don't collide */
  .dltoggle { display: flex; gap: 0; padding: .8rem 1rem 0; max-width: 1180px; margin: 0 auto; }
  .dltoggle button { background: var(--panel); border: 1px solid var(--line); color: var(--text);
    font-family: 'Space Grotesk', sans-serif; font-size: .72rem; text-transform: lowercase; letter-spacing: .06em;
    padding: .45em 1em; cursor: pointer; opacity: .55; border-right: none; }
  .dltoggle button:last-child { border-right: 1px solid var(--line); }
  .dltoggle button.active { opacity: 1; background: rgba(239,71,111,.25); }
  .dlview { display: none; } .dlview.active { display: block; }
  .dlrow-hidden { display: none !important; }
  /* video is ALWAYS a 3x3 thumbnail grid (not in the mockups — Jason's rule) */
  .dlvgrid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; padding: 12px; }
  .dlvgrid .vt { position: relative; aspect-ratio: 1; border-radius: 8px; overflow: hidden;
    border: 1px solid var(--line); background: var(--panel); display: block; text-decoration: none; color: var(--text); }
  .dlvgrid .vt img { width: 100%; height: 100%; object-fit: cover; }
  .dlvgrid .vt .cap { position: absolute; inset: auto 0 0 0; padding: .6rem .7rem; font-size: .8rem;
    font-weight: 600; color: var(--porcelain); background: linear-gradient(transparent, rgba(0,0,0,.85)); }
  @media (max-width: 768px) { .dlvgrid { grid-template-columns: 1fr; } }

  /* ===== ESPN (portal + module grid) ===== */
  #view-espn { font: 12px/1.4 Arial, Helvetica, sans-serif; }
  #view-espn .page { max-width: 1180px; margin: 0 auto; padding: 1rem; }
  #view-espn .subhead { display: flex; border-bottom: 3px solid var(--link); }
  #view-espn .subhead a { padding: 7px 14px; color: var(--text); font-weight: bold; font-size: 11px; cursor: pointer; text-decoration: none; }
  #view-espn .subhead a.active, #view-espn .subhead a:hover { background: var(--link); color: var(--porcelain); }
  #view-espn .content { display: flex; gap: 14px; margin-top: 12px; }
  #view-espn .span-4 { flex: 2; min-width: 0; } #view-espn .span-2 { flex: 1; min-width: 0; }
  #view-espn .mod { border: 1px solid var(--line); margin-bottom: 14px; background: var(--panel); }
  #view-espn .mod-h { border-bottom: 1px solid var(--line); padding: 5px 9px; font-size: 11px; font-weight: bold;
    letter-spacing: .5px; text-transform: uppercase; color: var(--porcelain); background: rgba(255,252,249,.05); }
  #view-espn .mod-f { border-top: 1px solid var(--line); padding: 4px 9px; font-size: 11px; }
  #view-espn .etabs { display: flex; border-bottom: 1px solid var(--line); }
  #view-espn .etabs a { padding: 6px 13px; font-size: 11px; font-weight: bold; text-transform: uppercase;
    color: var(--text); opacity: .6; border-right: 1px solid var(--line); cursor: pointer; text-decoration: none; }
  #view-espn .etabs a.active { opacity: 1; background: rgba(255,252,249,.06); }
  #view-espn .epane { display: none; } #view-espn .epane.active { display: block; }
  #view-espn .feat { padding: 11px; border-bottom: 1px solid var(--line); }
  #view-espn .feat h2 { font-size: 17px; margin-bottom: 3px; } #view-espn .feat p { color: var(--text); opacity: .85; }
  #view-espn .feat .meta { font-size: 10px; opacity: .55; margin-top: 4px; }
  #view-espn table { width: 100%; border-collapse: collapse; font-size: 12px; }
  #view-espn th { border: 0 1px 1px 0 solid var(--line); border-width: 0 1px 1px 0; padding: 3px 8px;
    text-align: left; font-size: 10px; text-transform: uppercase; color: var(--porcelain); opacity: .8; background: rgba(255,252,249,.05); }
  #view-espn td { border: 0 1px 1px 0 solid var(--line); border-width: 0 1px 1px 0; padding: 3px 8px; color: var(--text); }
  #view-espn tr:nth-child(even) td { background: rgba(255,252,249,.03); }
  #view-espn tr:hover td { background: rgba(239,71,111,.12); }
  #view-espn .num { text-align: right; font-variant-numeric: tabular-nums; }
  #view-espn .score-row { display: flex; justify-content: space-between; padding: 5px 9px; border-bottom: 1px solid var(--line); }
  #view-espn .ql li { list-style: none; border-bottom: 1px solid var(--line); } #view-espn .ql a { display: block; padding: 5px 9px; }

  /* ===== Napster (Win9x transfer list — the excel grid) ===== */
  #view-napster { font: 12px/1.5 Tahoma, "MS Sans Serif", Verdana, sans-serif; }
  #view-napster .win { max-width: 1180px; margin: 0 auto; background: var(--bg); border: 1px solid var(--line); }
  #view-napster .titlebar { background: linear-gradient(90deg, var(--link), var(--visited)); color: var(--porcelain); padding: 4px 8px; font-weight: bold; }
  #view-napster .menubar { background: rgba(255,252,249,.08); color: var(--porcelain); font-size: 11px; padding: 2px 6px; border-bottom: 1px solid var(--line); }
  #view-napster .menubar span { padding: 2px 8px; }
  #view-napster .toolbar { padding: 4px 6px; display: flex; gap: 4px; border-bottom: 1px solid var(--line); background: rgba(255,252,249,.05); }
  #view-napster .toolbar button { font: 11px Tahoma; padding: 3px 12px; background: var(--panel); border: 2px outset var(--line);
    cursor: pointer; color: var(--text); } #view-napster .toolbar button.down { border-style: inset; background: rgba(239,71,111,.2); }
  #view-napster .body { overflow: auto; border: 2px inset var(--line); margin: 6px; max-height: 70vh; }
  #view-napster table { width: 100%; border-collapse: collapse; font-size: 11px; }
  #view-napster th { background: rgba(255,252,249,.08); color: var(--porcelain); border: 2px outset var(--line); padding: 2px 8px; text-align: left; font-weight: normal; white-space: nowrap; }
  #view-napster td { padding: 2px 8px; white-space: nowrap; border-bottom: 1px solid var(--line); color: var(--text); }
  #view-napster tbody tr:hover td { background: var(--link); color: var(--porcelain); }
  #view-napster tbody tr:hover td a { color: var(--porcelain); }
  #view-napster .num { text-align: right; font-variant-numeric: tabular-nums; }
  #view-napster .ok { color: var(--visited); }
  #view-napster .statusbar { color: var(--porcelain); font-size: 11px; padding: 3px 8px; border-top: 1px solid var(--line); display: flex; background: rgba(255,252,249,.05); }
  #view-napster .statusbar div { border: 1px inset var(--line); padding: 1px 10px; margin-right: 4px; }
  #view-napster .npane { display: none; } #view-napster .npane.active { display: block; }
  #view-napster textarea { width: 100%; min-height: 8rem; background: var(--panel); color: var(--text); border: 2px inset var(--line); padding: .8rem; font: 12px Tahoma; }
  #view-napster .send { margin: .5rem; padding: 4px 14px; font: 11px Tahoma; background: var(--panel); border: 2px outset var(--line); color: var(--text); cursor: pointer; }

  /* ===== CNN (zones) ===== */
  #view-cnn { font: 14px/1.35 "Helvetica Neue", Arial, sans-serif; }
  #view-cnn .zn { max-width: 1140px; margin: 0 auto; padding: 20px 24px; }
  #view-cnn .znh { font-size: 22px; font-weight: bold; margin-bottom: 14px; color: var(--porcelain); border-bottom: 1px solid var(--line); padding-bottom: 8px; }
  #view-cnn .lead { display: flex; gap: 26px; } #view-cnn .fluid { flex: 1.6; min-width: 0; } #view-cnn .stack { flex: 1; min-width: 0; }
  #view-cnn .cd-lead .media { height: 320px; background: linear-gradient(160deg, var(--link), var(--bg)); display: flex; align-items: flex-end;
    padding: 14px; color: var(--porcelain); font-size: 12px; text-transform: uppercase; letter-spacing: 1px; border-radius: 6px 6px 0 0; }
  #view-cnn .cd-lead .hl { font-size: 28px; font-weight: bold; line-height: 1.15; padding: 14px 2px; }
  #view-cnn .cd-lead .dek { color: var(--text); opacity: .8; padding: 0 2px 10px; font-size: 15px; }
  #view-cnn .cd-small { border-bottom: 1px solid var(--line); padding: 10px 2px; }
  #view-cnn .cd-small .hl { font-size: 15px; font-weight: bold; } #view-cnn .icon { color: var(--link); font-weight: bold; margin-right: 6px; }
  #view-cnn .meta { font-size: 11px; opacity: .5; margin-top: 2px; }
  #view-cnn .row { display: flex; gap: 26px; flex-wrap: wrap; } #view-cnn .tile { flex: 1; min-width: 180px; }
  #view-cnn .tile .media { height: 120px; background: linear-gradient(160deg, var(--bg), #16344f); display: flex; align-items: flex-end;
    padding: 10px; color: var(--porcelain); font-size: 11px; text-transform: uppercase; letter-spacing: 1px; border: 1px solid var(--line); border-radius: 6px 6px 0 0; }
  #view-cnn .tile .hl { font-size: 15px; font-weight: bold; padding: 10px 2px 4px; }
  #view-cnn .t-dark { background: rgba(0,0,0,.2); }

  /* ===== iTunes (sidebar + library) ===== */
  #view-itunes { font: 12px/1.5 "Lucida Grande", "Helvetica Neue", Arial, sans-serif; }
  #view-itunes .win { max-width: 1180px; margin: 0 auto; display: flex; flex-direction: column; border: 1px solid var(--line); min-height: 60vh; }
  #view-itunes .tb { border-bottom: 1px solid var(--line); padding: 7px 12px; display: flex; align-items: center; gap: 10px; background: rgba(255,252,249,.05); }
  #view-itunes .tb .t { flex: 1; text-align: center; font-size: 12px; color: var(--porcelain); font-weight: bold; }
  #view-itunes .main { flex: 1; display: flex; min-height: 0; }
  #view-itunes .sidebar { width: 185px; background: var(--panel); border-right: 1px solid var(--line); padding-top: 8px; flex-shrink: 0; }
  #view-itunes .sidebar h3 { font-size: 10px; text-transform: uppercase; color: var(--porcelain); opacity: .6; padding: 6px 12px 2px; letter-spacing: .5px; }
  #view-itunes .sidebar li { list-style: none; padding: 3px 12px 3px 22px; cursor: pointer; color: var(--text); }
  #view-itunes .sidebar li.sel { background: linear-gradient(var(--link), #c22e52); color: var(--porcelain); font-weight: bold; }
  #view-itunes .lib { flex: 1; overflow: auto; max-height: 70vh; }
  #view-itunes table { width: 100%; border-collapse: collapse; font-size: 12px; }
  #view-itunes th { position: sticky; top: 0; background: rgba(255,252,249,.08); border-right: 1px solid var(--line); border-bottom: 1px solid var(--line);
    padding: 4px 10px; text-align: left; font-weight: normal; font-size: 11px; color: var(--porcelain); white-space: nowrap; }
  #view-itunes td { padding: 3px 10px; white-space: nowrap; color: var(--text); }
  #view-itunes tbody tr:nth-child(even) { background: rgba(255,252,249,.03); }
  #view-itunes tbody tr:hover { background: rgba(239,71,111,.12); }
  #view-itunes .num { text-align: right; font-variant-numeric: tabular-nums; }
  #view-itunes .statusbar { border-top: 1px solid var(--line); padding: 5px; text-align: center; font-size: 11px; color: var(--porcelain); opacity: .7; background: rgba(255,252,249,.05); }
</style>

<div class="dltoggle">
  <button class="active" data-view="espn">espn</button>
  <button data-view="napster">napster</button>
  <button data-view="cnn">cnn</button>
  <button data-view="itunes">itunes</button>
</div>

<?php
// shared cell helpers
function dl_a($s) { return '<a href="'.htmlspecialchars($s['url']).'" target="_blank" rel="noopener">'.htmlspecialchars($s['name']).'</a>'; }
function dl_t($s) { return htmlspecialchars(strtolower($s['name'].' '.$s['kind'].' '.$s['lede'])); }
function dl_vgrid($videos) {
  if (!$videos) return '<div style="padding:12px;opacity:.5">no video research yet</div>';
  $h = '<div class="dlvgrid">';
  foreach ($videos as $v) {
    $h .= '<a class="vt" href="'.htmlspecialchars($v['url']).'" target="_blank" rel="noopener" data-t="'.dl_t($v).'">';
    if (!empty($v['thumb'])) { $h .= '<img src="'.htmlspecialchars($v['thumb']).'" alt="">'; }
    $h .= '<span class="cap">'.htmlspecialchars($v['name']).'</span></a>';
  }
  return $h.'</div>';
}
?>

<!-- ============ ESPN ============ -->
<div class="dlview active" id="view-espn">
  <div class="page">
    <div class="subhead">
      <a class="active">index</a><a>subjects</a><a>videos</a><a>queue</a><a>notes</a>
    </div>
    <div class="content">
      <div class="span-4">
        <div class="mod">
          <div class="etabs"><a class="active" data-p="latest">Latest</a><a data-p="videos">Videos</a><a data-p="queue">Queue</a></div>
          <div class="epane active" id="e-latest">
            <?php if ($hero): ?>
            <div class="feat" data-t="<?= dl_t($hero) ?>">
              <h2><?= dl_a($hero) ?></h2>
              <p><?= htmlspecialchars($hero['lede']) ?></p>
              <div class="meta"><?= htmlspecialchars($hero['kind']) ?><?= $hero['date'] ? ' · '.htmlspecialchars($hero['date']) : '' ?></div>
            </div>
            <table>
              <tr><th>Subject</th><th>Kind</th><th>Date</th></tr>
              <?php foreach ($rest as $s): ?>
              <tr data-t="<?= dl_t($s) ?>"><td><?= dl_a($s) ?></td><td><?= htmlspecialchars($s['kind']) ?></td><td class="num"><?= htmlspecialchars($s['date']) ?></td></tr>
              <?php endforeach; ?>
            </table>
            <?php else: ?><div class="feat">no research yet</div><?php endif; ?>
          </div>
          <div class="epane" id="e-videos"><?= dl_vgrid($videos) ?></div>
          <div class="epane" id="e-queue"><table id="espn-queue"><tr><th>Item</th><th>Status</th></tr></table></div>
        </div>
        <div class="mod">
          <div class="mod-h">All subjects</div>
          <table>
            <tr><th>Subject</th><th>Kind</th><th>Date</th><th>Status</th></tr>
            <?php foreach ($subjects as $s): ?>
            <tr data-t="<?= dl_t($s) ?>"><td><?= dl_a($s) ?></td><td><?= htmlspecialchars($s['kind']) ?></td><td class="num"><?= htmlspecialchars($s['date']) ?></td><td>researched</td></tr>
            <?php endforeach; ?>
          </table>
          <div class="mod-f"><?= count($subjects) ?> subjects</div>
        </div>
      </div>
      <div class="span-2">
        <div class="mod"><div class="mod-h">Pipeline</div>
          <div class="score-row"><span>Subjects</span><b><?= count($subjects) ?></b></div>
          <div class="score-row"><span>Videos</span><b><?= count($videos) ?></b></div>
        </div>
        <div class="mod"><div class="mod-h">Recent videos</div>
          <ul class="ql"><?php foreach (array_slice($videos,0,5) as $v): ?><li><?= dl_a($v) ?></li><?php endforeach; ?></ul>
        </div>
      </div>
    </div>
  </div>
</div>

<!-- ============ NAPSTER (transfer-list grid) ============ -->
<div class="dlview" id="view-napster">
  <div class="win">
    <div class="titlebar">doubled.life</div>
    <div class="menubar"><span>File</span><span>Actions</span><span>View</span><span>Help</span></div>
    <div class="toolbar">
      <button class="down" data-np="library">Library</button><button data-np="videos">Videos</button><button data-np="queue">Queue</button><button data-np="notes">Notes</button>
    </div>
    <div class="npane active" id="n-library"><div class="body"><table>
      <thead><tr><th style="width:34%">Subject</th><th>Kind</th><th>Sources</th><th>Date</th><th>Status</th></tr></thead>
      <tbody>
        <?php foreach ($subjects as $s): ?>
        <tr data-t="<?= dl_t($s) ?>"><td><?= dl_a($s) ?></td><td><?= htmlspecialchars($s['kind']) ?></td><td class="num">–</td><td class="num"><?= htmlspecialchars($s['date']) ?></td><td class="ok">researched</td></tr>
        <?php endforeach; ?>
      </tbody></table></div></div>
    <div class="npane" id="n-videos"><div class="body"><?= dl_vgrid($videos) ?></div></div>
    <div class="npane" id="n-queue"><div class="body"><table><thead><tr><th style="width:50%">Item</th><th>Status</th><th>Detail</th></tr></thead><tbody id="napster-queue"></tbody></table></div></div>
    <div class="npane" id="n-notes"><div class="body" style="padding:.6rem">
      <form method="post"><textarea name="note" placeholder="a note for hermes — recorded for planning"></textarea><button class="send" type="submit">Send</button>
      <div style="font-size:11px;opacity:.6;padding:.3rem"><?= $note_ok ? 'sent — hermes will log it' : '' ?></div></form></div></div>
    <div class="statusbar"><div>Online</div><div><?= count($subjects) ?> subjects</div><div><?= count($videos) ?> videos</div></div>
  </div>
</div>

<!-- ============ CNN (zones) ============ -->
<div class="dlview" id="view-cnn">
  <?php if ($hero): ?>
  <section class="zn">
    <div class="lead">
      <div class="fluid"><div class="cd-lead" data-t="<?= dl_t($hero) ?>">
        <div class="media"><?= htmlspecialchars($hero['kind']) ?></div>
        <div class="hl"><?= dl_a($hero) ?></div>
        <div class="dek"><?= htmlspecialchars($hero['lede']) ?></div>
      </div></div>
      <div class="stack">
        <?php foreach (array_slice($rest,0,7) as $s): ?>
        <div class="cd-small" data-t="<?= dl_t($s) ?>"><div class="hl"><span class="icon">›</span><?= dl_a($s) ?></div>
          <div class="meta"><?= htmlspecialchars($s['kind']) ?> · <?= htmlspecialchars($s['date']) ?></div></div>
        <?php endforeach; ?>
      </div>
    </div>
  </section>
  <section class="zn"><div class="znh">Recent research</div><div class="row">
    <?php foreach (array_slice($subjects,0,4) as $s): ?>
    <div class="tile" data-t="<?= dl_t($s) ?>"><div class="media"><?= htmlspecialchars($s['kind']) ?></div>
      <div class="hl"><?= dl_a($s) ?></div><div class="meta" style="padding:0 2px 10px"><?= htmlspecialchars($s['date']) ?></div></div>
    <?php endforeach; ?>
  </div></section>
  <section class="zn t-dark"><div class="znh">Videos</div><?= dl_vgrid($videos) ?></section>
  <?php else: ?><section class="zn">no research yet</section><?php endif; ?>
</div>

<!-- ============ iTunes (sidebar + library) ============ -->
<div class="dlview" id="view-itunes">
  <div class="win">
    <div class="tb"><div class="t">doubled.life</div></div>
    <div class="main">
      <div class="sidebar">
        <h3>Library</h3>
        <ul><li class="sel" data-f="">All subjects</li><li data-f="venue">Venues</li><li data-f="video">Videos</li><li data-f="concept">Concepts</li><li data-f="synthesis">Synthesis</li></ul>
      </div>
      <div class="lib"><table>
        <thead><tr><th style="width:36%">Name</th><th>Kind</th><th>Date Added</th><th>Status</th></tr></thead>
        <tbody>
          <?php foreach ($subjects as $s): ?>
          <tr data-t="<?= dl_t($s) ?>" data-kind="<?= htmlspecialchars($s['kind']) ?>"><td><?= dl_a($s) ?></td><td><?= htmlspecialchars($s['kind']) ?></td><td class="num"><?= htmlspecialchars($s['date']) ?></td><td>researched</td></tr>
          <?php endforeach; ?>
        </tbody>
      </table></div>
    </div>
    <div class="statusbar"><?= count($subjects) ?> subjects · <?= count($videos) ?> videos</div>
  </div>
</div>

<script>
const q = document.getElementById('q');
function esc(s){ return (s||'').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
function activeView(){ return document.querySelector('.dlview.active'); }
function filter(){ const t=(q.value||'').toLowerCase();
  activeView().querySelectorAll('[data-t]').forEach(el => { el.classList.toggle('dlrow-hidden', !el.dataset.t.includes(t)); }); }
q && q.addEventListener('input', filter);

// view toggle (espn default, persisted)
function setView(v){
  document.querySelectorAll('.dltoggle button').forEach(b => b.classList.toggle('active', b.dataset.view===v));
  document.querySelectorAll('.dlview').forEach(x => x.classList.toggle('active', x.id==='view-'+v));
  try { localStorage.setItem('dl_view', v); } catch(e){}
  filter();
  if (v==='espn' || v==='napster') loadQueue();
}
document.querySelectorAll('.dltoggle button').forEach(b => b.addEventListener('click', () => setView(b.dataset.view)));
try { const s=localStorage.getItem('dl_view'); if (s) setView(s); } catch(e){}

// ESPN internal tabs
document.querySelectorAll('#view-espn .etabs a').forEach(a => a.addEventListener('click', () => {
  document.querySelectorAll('#view-espn .etabs a').forEach(x=>x.classList.remove('active'));
  document.querySelectorAll('#view-espn .epane').forEach(x=>x.classList.remove('active'));
  a.classList.add('active'); document.getElementById('e-'+a.dataset.p).classList.add('active');
  if (a.dataset.p==='queue') loadQueue();
}));
// Napster toolbar
document.querySelectorAll('#view-napster .toolbar button').forEach(b => b.addEventListener('click', () => {
  document.querySelectorAll('#view-napster .toolbar button').forEach(x=>x.classList.remove('down'));
  document.querySelectorAll('#view-napster .npane').forEach(x=>x.classList.remove('active'));
  b.classList.add('down'); document.getElementById('n-'+b.dataset.np).classList.add('active');
  if (b.dataset.np==='queue') loadQueue();
}));
// iTunes sidebar filter
document.querySelectorAll('#view-itunes .sidebar li').forEach(li => li.addEventListener('click', () => {
  document.querySelectorAll('#view-itunes .sidebar li').forEach(x=>x.classList.remove('sel')); li.classList.add('sel');
  const f=li.dataset.f;
  document.querySelectorAll('#view-itunes tbody tr').forEach(tr => tr.classList.toggle('dlrow-hidden', f && tr.dataset.kind!==f));
}));

function queueRows(jobs){
  return jobs.map(j => {
    const link = j.url ? '<a href="'+esc(j.url)+'" target="_blank" rel="noopener">'+esc(j.target)+'</a>' : esc(j.target||'request');
    return '<tr data-t="'+esc((j.target||'').toLowerCase())+'"><td>'+link+'</td><td class="ok">'+esc(j.status||'')+'</td><td>'+esc(j.detail||'')+'</td></tr>';
  }).join('') || '<tr><td colspan="3">nothing in the last 24 hours</td></tr>';
}
function loadQueue(){
  fetch('gate_status.php').then(r=>r.json()).then(d=>{
    const jobs=(d&&d.jobs)||[];
    const nq=document.getElementById('napster-queue'); if(nq) nq.innerHTML=queueRows(jobs);
    const eq=document.getElementById('espn-queue');
    if(eq) eq.innerHTML='<tr><th>Item</th><th>Status</th></tr>'+jobs.map(j=>'<tr><td>'+(j.url?'<a href="'+esc(j.url)+'" target="_blank" rel="noopener">'+esc(j.target)+'</a>':esc(j.target))+'</td><td>'+esc(j.status)+'</td></tr>').join('');
  }).catch(()=>{});
}
</script>
