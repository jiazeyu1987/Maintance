'use strict';
const tabs = [...document.querySelectorAll('[role="tab"]')];
function activate(tab) {
  for (const item of tabs) {
    const selected = item === tab;
    item.setAttribute('aria-selected', String(selected));
    item.tabIndex = selected ? 0 : -1;
    document.getElementById(item.getAttribute('aria-controls')).hidden = !selected;
  }
}
tabs.forEach((tab, index) => {
  tab.addEventListener('click', () => activate(tab));
  tab.addEventListener('keydown', event => {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    const next = event.key === 'Home' ? tabs[0] : event.key === 'End' ? tabs.at(-1) : tabs[(index + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length];
    activate(next); next.focus();
  });
});
document.querySelectorAll('[name="type"]').forEach(input => input.addEventListener('change', () => {
  document.getElementById('backup-note').textContent = input.value === 'FULL' ? '全量备份将保存完整数据。' : '系统将自动关联有效备份基线；没有可用基线时，需先做全量备份。';
}));
const dialog = document.getElementById('confirmation');
for (const form of document.querySelectorAll('form')) {
  form.addEventListener('submit', event => {
    event.preventDefault();
    const backup = form.id === 'backup-panel';
    const server = form.elements.namedItem('server');
    const entries = [['服务器', server.selectedOptions[0].textContent], ['NAS 地址', form.elements.namedItem('nas').value.trim()]];
    if (backup) entries.push(['备份类型', form.elements.namedItem('type').value === 'FULL' ? '全量备份' : '增量备份（自动关联基线）']);
    else entries.push(['备份包', form.elements.namedItem('package').selectedOptions[0].textContent]);
    document.getElementById('confirmation-title').textContent = backup ? '确认备份配置' : '确认恢复配置';
    const summary = document.getElementById('summary'); summary.replaceChildren();
    entries.forEach(([label, value]) => {
      const term = document.createElement('dt'); term.textContent = label;
      const detail = document.createElement('dd'); detail.textContent = value;
      summary.append(term, detail);
    });
    dialog.showModal();
  });
}
document.getElementById('close-dialog').addEventListener('click', () => dialog.close());
