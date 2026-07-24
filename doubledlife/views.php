<?php
// Guard: only render when included by the authed index (never on direct hit).
if (!isset($subjects)) { http_response_code(404); exit; }
// doubled.life authed view — four skeuomorphic index shells (ESPN/Napster/CNN/
// iTunes) over ONE consistent tab system: every view has Library / Videos /
// Queue / Notes, one pink-underline active state, video is always the 3x3 grid.
// Distinct bodies, unified controls. Included by index.php in the authed branch.
$hero = $subjects[0] ?? null;
$rest = array_slice($subjects, 1);

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
function dl_queue_pane($view) {
  return '<div class="dlqueue"><table class="dlq"><thead><tr><th style="width:48%">Item</th><th>Status</th><th>Detail</th></tr></thead>'
       . '<tbody class="dlq-body" data-q="'.$view.'"><tr><td colspan="3" style="opacity:.5">loading…</td></tr></tbody></table></div>';
}
function dl_notes_pane($note_ok) {
  return '<form method="post" class="dlnotes"><textarea name="note" placeholder="a note for hermes — recorded for planning alongside the research corpus"></textarea>'
       . '<button type="submit">send to hermes</button><div class="hint">'
       . ($note_ok ? 'sent — hermes will log it' : 'goes into hermes planning') . '</div></form>';
}
// tab bar for the top-tab views (espn/napster/cnn); iTunes uses its sidebar.
function dl_tabbar() {
  $t = ['library'=>'Library','videos'=>'Videos','queue'=>'Queue','notes'=>'Notes'];
  $h = '<div class="dltabs">'; $first = true;
  foreach ($t as $k=>$label) { $h .= '<a class="dltab'.($first?' active':'').'" data-tab="'.$k.'">'.$label.'</a>'; $first=false; }
  return $h.'</div>';
}
?>
<style>
  /* ---- unified controls (same across all four views) ---- */
  .dlhead { display:flex; align-items:center; justify-content:space-between; max-width:1180px; margin:0 auto; padding:1rem 1rem .2rem; }
  .dlwm { font-size:1.4rem; font-weight:600; letter-spacing:.04em; color:var(--text); font-family:'Space Grotesk',sans-serif; }
  .dlhead input { background:var(--panel); border:1px solid var(--line); color:var(--text); font-family:'Space Grotesk',sans-serif; font-size:.9rem; padding:.45em 1em; border-radius:8px; width:14rem; }
  .dltoggle { display:flex; gap:0; padding:.4rem 1rem .2rem; max-width:1180px; margin:0 auto; }
  .dltoggle button { background:var(--panel); border:1px solid var(--line); color:var(--text);
    font-family:'Space Grotesk',sans-serif; font-size:.72rem; text-transform:lowercase; letter-spacing:.06em;
    padding:.45em 1em; cursor:pointer; opacity:.55; border-right:none; }
  .dltoggle button:last-child { border-right:1px solid var(--line); }
  .dltoggle button.active { opacity:1; color:var(--link); }
  .dlview { display:none; } .dlview.active { display:block; }
  .dlrow-hidden { display:none !important; }
  /* content links: just underlined, in text color. pink is reserved for tabs. */
  .dlview a { color:inherit; text-decoration:underline; text-underline-offset:2px; }
  .dlview a:visited { color:var(--visited); }        /* clicked = golden pollen */
  /* unified tab bar + active = pink underline (identical everywhere) */
  .dltabs { display:flex; border-bottom:1px solid var(--line); }
  .dltab { padding:.5em 1.1em; cursor:pointer; text-decoration:none !important; color:var(--text);
    opacity:.55; border-bottom:2px solid transparent; font-weight:600; font-size:.8rem; }
  .dltab:hover { opacity:.85; }
  .dltab.active { opacity:1; color:var(--link); border-bottom-color:var(--link); }
  .dlpane { display:none; } .dlpane.active { display:block; }
  .dlqueue { padding:8px; } .dlq { width:100%; border-collapse:collapse; }
  .dlq th, .dlq td { text-align:left; padding:4px 8px; border-bottom:1px solid var(--line); }
  .dlq th { color:var(--porcelain); opacity:.7; font-size:.72rem; text-transform:uppercase; }
  .dlnotes { padding:12px; } .dlnotes textarea { width:100%; min-height:8rem; background:var(--panel);
    color:var(--text); border:1px solid var(--line); border-radius:8px; padding:1rem; font-family:inherit; font-size:.95rem; }
  .dlnotes button { margin-top:.7rem; background:var(--panel); border:1px solid var(--line); color:var(--text);
    font-family:inherit; padding:.5em 1.3em; border-radius:8px; cursor:pointer; }
  .dlnotes .hint { font-size:.78rem; opacity:.5; margin-top:.5rem; }
  /* video is ALWAYS a 3x3 thumbnail grid (Jason's rule; not in the mockups) */
  .dlvgrid { display:grid; grid-template-columns:repeat(3,1fr); gap:12px; padding:12px; }
  .dlvgrid .vt { position:relative; aspect-ratio:1; border-radius:8px; overflow:hidden; border:1px solid var(--line);
    background:var(--panel); display:block; text-decoration:none !important; color:var(--text); }
  .dlvgrid .vt img { width:100%; height:100%; object-fit:cover; }
  .dlvgrid .vt .cap { position:absolute; inset:auto 0 0 0; padding:.6rem .7rem; font-size:.8rem; font-weight:600;
    color:var(--porcelain); background:linear-gradient(transparent, rgba(0,0,0,.85)); }
  @media (max-width:768px) { .dlvgrid { grid-template-columns:1fr; } }

  /* ===== ESPN portal body ===== */
  #view-espn { font:12px/1.4 Arial, Helvetica, sans-serif; }
  #view-espn .page { max-width:1180px; margin:0 auto; padding:1rem; }
  #view-espn .content { display:flex; gap:14px; margin-top:12px; }
  #view-espn .span-4 { flex:2; min-width:0; } #view-espn .span-2 { flex:1; min-width:0; }
  #view-espn .mod { border:1px solid var(--line); margin-bottom:14px; background:var(--panel); }
  #view-espn .mod-h { border-bottom:1px solid var(--line); padding:5px 9px; font-size:11px; font-weight:bold;
    letter-spacing:.5px; text-transform:uppercase; color:var(--porcelain); background:rgba(255,252,249,.05); }
  #view-espn .feat { padding:11px; border-bottom:1px solid var(--line); }
  #view-espn .feat h2 { font-size:17px; margin-bottom:3px; } #view-espn .feat p { opacity:.85; }
  #view-espn .feat .meta { font-size:10px; opacity:.55; margin-top:4px; }
  #view-espn table { width:100%; border-collapse:collapse; font-size:12px; }
  #view-espn th { border-width:0 1px 1px 0; border-style:solid; border-color:var(--line); padding:3px 8px;
    text-align:left; font-size:10px; text-transform:uppercase; color:var(--porcelain); opacity:.8; background:rgba(255,252,249,.05); }
  #view-espn td { border-width:0 1px 1px 0; border-style:solid; border-color:var(--line); padding:3px 8px; }
  #view-espn tr:nth-child(even) td { background:rgba(255,252,249,.03); }
  #view-espn tr:hover td { background:rgba(239,71,111,.12); }
  #view-espn .num { text-align:right; font-variant-numeric:tabular-nums; }
  #view-espn .score-row { display:flex; justify-content:space-between; padding:5px 9px; border-bottom:1px solid var(--line); }
  #view-espn .ql li { list-style:none; border-bottom:1px solid var(--line); } #view-espn .ql a { display:block; padding:5px 9px; }

  /* ===== Napster window body ===== */
  #view-napster { font:12px/1.5 Tahoma, "MS Sans Serif", Verdana, sans-serif; }
  #view-napster .win { max-width:1180px; margin:0 auto; background:var(--bg); border:1px solid var(--line); }
  #view-napster .titlebar { background:linear-gradient(90deg, var(--link), var(--visited)); color:var(--porcelain); padding:4px 8px; font-weight:bold; }
  #view-napster .body { overflow:auto; border:2px inset var(--line); margin:6px; max-height:70vh; }
  #view-napster table { width:100%; border-collapse:collapse; font-size:11px; }
  #view-napster th { background:rgba(255,252,249,.08); color:var(--porcelain); border:2px outset var(--line); padding:2px 8px; text-align:left; font-weight:normal; white-space:nowrap; }
  #view-napster td { padding:2px 8px; white-space:nowrap; border-bottom:1px solid var(--line); }
  #view-napster tbody tr:hover td { background:var(--link); color:var(--porcelain); }
  #view-napster .num { text-align:right; font-variant-numeric:tabular-nums; } #view-napster .ok { color:var(--visited); }
  #view-napster .statusbar { color:var(--porcelain); font-size:11px; padding:3px 8px; border-top:1px solid var(--line); display:flex; background:rgba(255,252,249,.05); }
  #view-napster .statusbar div { border:1px inset var(--line); padding:1px 10px; margin-right:4px; }

  /* ===== CNN zones body ===== */
  #view-cnn { font:14px/1.35 "Helvetica Neue", Arial, sans-serif; }
  #view-cnn .zn { max-width:1140px; margin:0 auto; padding:16px 24px; }
  #view-cnn .znh { font-size:20px; font-weight:bold; margin-bottom:12px; color:var(--porcelain); border-bottom:1px solid var(--line); padding-bottom:8px; }
  #view-cnn .lead { display:flex; gap:26px; } #view-cnn .fluid { flex:1.6; min-width:0; } #view-cnn .stack { flex:1; min-width:0; }
  #view-cnn .cd-lead .media { height:300px; background:linear-gradient(160deg, var(--link), var(--bg)); display:flex; align-items:flex-end;
    padding:14px; color:var(--porcelain); font-size:12px; text-transform:uppercase; letter-spacing:1px; border-radius:6px 6px 0 0; }
  #view-cnn .cd-lead .hl { font-size:26px; font-weight:bold; line-height:1.15; padding:14px 2px; }
  #view-cnn .cd-lead .dek { opacity:.8; padding:0 2px 10px; font-size:15px; }
  #view-cnn .cd-small { border-bottom:1px solid var(--line); padding:10px 2px; }
  #view-cnn .cd-small .hl { font-size:15px; font-weight:bold; } #view-cnn .icon { color:var(--link); font-weight:bold; margin-right:6px; }
  #view-cnn .meta { font-size:11px; opacity:.5; margin-top:2px; }

  /* ===== iTunes body (sidebar IS the nav) ===== */
  #view-itunes { font:12px/1.5 "Lucida Grande", "Helvetica Neue", Arial, sans-serif; }
  #view-itunes .win { max-width:1180px; margin:0 auto; display:flex; flex-direction:column; border:1px solid var(--line); min-height:60vh; }
  #view-itunes .tb { border-bottom:1px solid var(--line); padding:7px 12px; text-align:center; color:var(--porcelain); font-weight:bold; background:rgba(255,252,249,.05); }
  #view-itunes .main { flex:1; display:flex; min-height:0; }
  #view-itunes .sidebar { width:185px; background:var(--panel); border-right:1px solid var(--line); padding-top:8px; flex-shrink:0; }
  #view-itunes .sidebar h3 { font-size:10px; text-transform:uppercase; color:var(--porcelain); opacity:.6; padding:6px 12px 2px; letter-spacing:.5px; }
  #view-itunes .sidebar .dltab { display:block; padding:4px 12px 4px 18px; cursor:pointer; color:var(--text);
    border-bottom:0; border-left:3px solid transparent; opacity:.7; font-weight:400; }
  #view-itunes .sidebar .dltab.active { opacity:1; color:var(--link); border-left-color:var(--link); }
  #view-itunes .content { flex:1; overflow:auto; max-height:72vh; }
  #view-itunes table { width:100%; border-collapse:collapse; font-size:12px; }
  #view-itunes th { position:sticky; top:0; background:rgba(255,252,249,.08); border-right:1px solid var(--line); border-bottom:1px solid var(--line);
    padding:4px 10px; text-align:left; font-weight:normal; font-size:11px; color:var(--porcelain); white-space:nowrap; }
  #view-itunes td { padding:3px 10px; white-space:nowrap; }
  #view-itunes tbody tr:nth-child(even) { background:rgba(255,252,249,.03); }
  #view-itunes tbody tr:hover { background:rgba(239,71,111,.12); }
  #view-itunes .num { text-align:right; font-variant-numeric:tabular-nums; }
  #view-itunes .statusbar { border-top:1px solid var(--line); padding:5px; text-align:center; font-size:11px; color:var(--porcelain); opacity:.7; background:rgba(255,252,249,.05); }
</style>

<div class="dlhead"><span class="dlwm">doubled.life</span><input type="search" id="q" placeholder="search"></div>
<div class="dltoggle">
  <button class="active" data-view="espn">espn</button>
  <button data-view="napster">napster</button>
  <button data-view="cnn">cnn</button>
  <button data-view="itunes">itunes</button>
</div>

<!-- ============ ESPN ============ -->
<div class="dlview active" id="view-espn">
  <div class="page">
    <?= dl_tabbar() ?>
    <div class="content">
      <div class="span-4">
        <div class="dlpane active" data-pane="library">
          <div class="mod">
            <?php if ($hero): ?>
            <div class="feat" data-t="<?= dl_t($hero) ?>">
              <h2><?= dl_a($hero) ?></h2><p><?= htmlspecialchars($hero['lede']) ?></p>
              <div class="meta"><?= htmlspecialchars($hero['kind']) ?><?= $hero['date'] ? ' · '.htmlspecialchars($hero['date']) : '' ?></div>
            </div>
            <table><tr><th>Subject</th><th>Kind</th><th>Date</th></tr>
              <?php foreach ($rest as $s): ?>
              <tr data-t="<?= dl_t($s) ?>"><td><?= dl_a($s) ?></td><td><?= htmlspecialchars($s['kind']) ?></td><td class="num"><?= htmlspecialchars($s['date']) ?></td></tr>
              <?php endforeach; ?>
            </table>
            <?php else: ?><div class="feat">no research yet</div><?php endif; ?>
          </div>
        </div>
        <div class="dlpane" data-pane="videos"><?= dl_vgrid($videos) ?></div>
        <div class="dlpane" data-pane="queue"><?= dl_queue_pane('espn') ?></div>
        <div class="dlpane" data-pane="notes"><?= dl_notes_pane($note_ok) ?></div>
      </div>
      <div class="span-2">
        <div class="mod"><div class="mod-h">Pipeline</div>
          <div class="score-row"><span>Subjects</span><b><?= count($subjects) ?></b></div>
          <div class="score-row"><span>Videos</span><b><?= count($videos) ?></b></div>
        </div>
      </div>
    </div>
  </div>
</div>

<!-- ============ NAPSTER (transfer-list grid) ============ -->
<div class="dlview" id="view-napster">
  <div class="win">
    <?= dl_tabbar() ?>
    <div class="dlpane active" data-pane="library"><div class="body"><table>
      <thead><tr><th style="width:40%">Subject</th><th>Kind</th><th>Date</th><th>Status</th></tr></thead>
      <tbody><?php foreach ($subjects as $s): ?>
        <tr data-t="<?= dl_t($s) ?>"><td><?= dl_a($s) ?></td><td><?= htmlspecialchars($s['kind']) ?></td><td class="num"><?= htmlspecialchars($s['date']) ?></td><td class="ok">researched</td></tr>
      <?php endforeach; ?></tbody></table></div></div>
    <div class="dlpane" data-pane="videos"><div class="body"><?= dl_vgrid($videos) ?></div></div>
    <div class="dlpane" data-pane="queue"><div class="body"><?= dl_queue_pane('napster') ?></div></div>
    <div class="dlpane" data-pane="notes"><div class="body"><?= dl_notes_pane($note_ok) ?></div></div>
    <div class="statusbar"><div>Online</div><div><?= count($subjects) ?> subjects</div><div><?= count($videos) ?> videos</div></div>
  </div>
</div>

<!-- ============ CNN (zones) ============ -->
<div class="dlview" id="view-cnn">
  <div class="zn" style="padding-bottom:0"><?= dl_tabbar() ?></div>
  <div class="dlpane active" data-pane="library">
    <?php if ($hero): ?>
    <section class="zn"><div class="lead">
      <div class="fluid"><div class="cd-lead" data-t="<?= dl_t($hero) ?>">
        <div class="media"><?= htmlspecialchars($hero['kind']) ?></div>
        <div class="hl"><?= dl_a($hero) ?></div><div class="dek"><?= htmlspecialchars($hero['lede']) ?></div>
      </div></div>
      <div class="stack"><?php foreach ($rest as $s): ?>
        <div class="cd-small" data-t="<?= dl_t($s) ?>"><div class="hl"><span class="icon">›</span><?= dl_a($s) ?></div>
          <div class="meta"><?= htmlspecialchars($s['kind']) ?> · <?= htmlspecialchars($s['date']) ?></div></div>
      <?php endforeach; ?></div>
    </div></section>
    <?php else: ?><section class="zn">no research yet</section><?php endif; ?>
  </div>
  <div class="dlpane" data-pane="videos"><section class="zn"><?= dl_vgrid($videos) ?></section></div>
  <div class="dlpane" data-pane="queue"><section class="zn"><?= dl_queue_pane('cnn') ?></section></div>
  <div class="dlpane" data-pane="notes"><section class="zn"><?= dl_notes_pane($note_ok) ?></section></div>
</div>

<!-- ============ iTunes (sidebar nav) ============ -->
<div class="dlview" id="view-itunes">
  <div class="win">
    <div class="main">
      <div class="sidebar">
        <a class="dltab active" data-tab="library">Library</a>
        <a class="dltab" data-tab="videos">Videos</a>
        <a class="dltab" data-tab="queue">Queue</a>
        <a class="dltab" data-tab="notes">Notes</a>
      </div>
      <div class="content">
        <div class="dlpane active" data-pane="library"><table>
          <thead><tr><th style="width:38%">Name</th><th>Kind</th><th>Date Added</th><th>Status</th></tr></thead>
          <tbody><?php foreach ($subjects as $s): ?>
            <tr data-t="<?= dl_t($s) ?>"><td><?= dl_a($s) ?></td><td><?= htmlspecialchars($s['kind']) ?></td><td class="num"><?= htmlspecialchars($s['date']) ?></td><td>researched</td></tr>
          <?php endforeach; ?></tbody></table></div>
        <div class="dlpane" data-pane="videos"><?= dl_vgrid($videos) ?></div>
        <div class="dlpane" data-pane="queue"><?= dl_queue_pane('itunes') ?></div>
        <div class="dlpane" data-pane="notes"><?= dl_notes_pane($note_ok) ?></div>
      </div>
    </div>
    <div class="statusbar"><?= count($subjects) ?> subjects · <?= count($videos) ?> videos</div>
  </div>
</div>

<script>
const q = document.getElementById('q');
function esc(s){ return (s||'').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
function activeView(){ return document.querySelector('.dlview.active'); }
function filter(){ const t=(q.value||'').toLowerCase();
  activeView().querySelectorAll('[data-t]').forEach(el => el.classList.toggle('dlrow-hidden', !el.dataset.t.includes(t))); }
q && q.addEventListener('input', filter);

function setView(v){
  document.querySelectorAll('.dltoggle button').forEach(b => b.classList.toggle('active', b.dataset.view===v));
  document.querySelectorAll('.dlview').forEach(x => x.classList.toggle('active', x.id==='view-'+v));
  try { localStorage.setItem('dl_view', v); } catch(e){}
  filter();
  if (activeView().querySelector('.dltab.active')?.dataset.tab === 'queue') loadQueue();
}
document.querySelectorAll('.dltoggle button').forEach(b => b.addEventListener('click', () => setView(b.dataset.view)));
try { const s=localStorage.getItem('dl_view'); if (s) setView(s); } catch(e){}

// one tab handler for every view: switch panes within the clicked tab's view
document.querySelectorAll('.dltab').forEach(tab => tab.addEventListener('click', () => {
  const view = tab.closest('.dlview');
  view.querySelectorAll('.dltab').forEach(t => t.classList.remove('active'));
  view.querySelectorAll('.dlpane').forEach(p => p.classList.remove('active'));
  tab.classList.add('active');
  const pane = view.querySelector('.dlpane[data-pane="'+tab.dataset.tab+'"]');
  if (pane) pane.classList.add('active');
  if (tab.dataset.tab === 'queue') loadQueue();
  filter();
}));

function loadQueue(){
  fetch('gate_status.php').then(r=>r.json()).then(d=>{
    const jobs=(d&&d.jobs)||[];
    const rows = jobs.map(j => {
      const link = j.url ? '<a href="'+esc(j.url)+'" target="_blank" rel="noopener">'+esc(j.target)+'</a>' : esc(j.target||'request');
      return '<tr data-t="'+esc((j.target||'').toLowerCase())+'"><td>'+link+'</td><td>'+esc(j.status||'')+'</td><td>'+esc(j.detail||'')+'</td></tr>';
    }).join('') || '<tr><td colspan="3" style="opacity:.5">nothing in the last 24 hours</td></tr>';
    document.querySelectorAll('.dlq-body').forEach(tb => tb.innerHTML = rows);
  }).catch(()=>{});
}
</script>
