"""Room-wide repeating reward goals. Progress is persisted separately from configuration."""
import json
import os
import re
import tempfile
import time
from pathlib import Path
from collections import deque

KINDS = ('like', 'follow', 'comment', 'share', 'coins')
PATH = Path(__file__).with_name('milestone-progress.json')
MAX_INTEGER = 9007199254740991  # exact across Python / JSON / browser


def settings(config):
    raw = config.get('milestones', {})
    if not isinstance(raw, dict):
        raise ValueError('Cấu hình mốc không hợp lệ')
    result = {}
    for kind, fallback in zip(KINDS, ('skeleton', 'creeper', 'zombie', 'enderman', 'iron_golem')):
        target = str(config.get(kind + '_mob_type', fallback))
        if not target.startswith(('item:', 'special:')) and ':' not in target:
            target = 'minecraft:' + target
        group = raw.get(kind, {'enabled': kind != 'coins', 'rules': [{
            'id': kind + '-default', 'threshold': config.get('likes_per_skeleton', 50) if kind == 'like' else 100 if kind == 'coins' else 1,
            'reward': target, 'amount': config.get(kind + '_spawn_count', 1)}]})
        if not isinstance(group, dict) or not isinstance(group.get('enabled'), bool) or not isinstance(group.get('rules'), list):
            raise ValueError('Mốc ' + kind + ' không hợp lệ')
        rules, ids = [], set()
        for rule in group['rules']:
            if not isinstance(rule, dict):
                raise ValueError('Dòng mốc không hợp lệ')
            ident, reward = rule.get('id'), rule.get('reward')
            if not isinstance(ident, str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}', ident) or ident in ids:
                raise ValueError('ID mốc không hợp lệ hoặc trùng')
            ids.add(ident)
            if not isinstance(reward, str) or not re.fullmatch(r'(?:(?:item|special):)?[a-z0-9_.:-]+', reward):
                raise ValueError('Chọn phần thưởng hợp lệ cho mốc')
            cleaned = {'id': ident, 'reward': reward}
            for field in ('threshold', 'amount'):
                value = rule.get(field)
                if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= MAX_INTEGER:
                    raise ValueError('Mốc và số lượng phải là số nguyên dương')
                cleaned[field] = value
            rules.append(cleaned)
        remember = group.get('remember', False)
        if not isinstance(remember, bool):
            raise ValueError('Ghi nhớ phải là bật hoặc tắt')
        result[kind] = {'enabled': group['enabled'], 'rules': rules}
        if 'remember' in group:
            result[kind]['remember'] = remember
    return result


def snapshot(config=None, active=True):
    try:
        data = json.loads(PATH.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        data = {'groups': {}, 'updated': 0}
    if not active and config is not None:
        # Use current settings: an old snapshot may still have remember enabled.
        groups = data.setdefault('groups', {})
        for kind, group in settings(config).items():
            if not group.get('remember', False):
                groups[kind] = {**group, 'total': 0, 'rules': [
                    {**rule, 'current': 0, 'completed': 0} for rule in group['rules']]}
        data['pending'] = 0
    return data


class Milestones:
    def __init__(self, config, send, config_path=None, path=None):
        self.config, self.send = config, send
        self.config_path, self.path = config_path, path or PATH
        self.groups, self.counters, self.completed = {}, {}, {}
        self.pending = deque()
        self.stamp = None
        self.session_id = None
        try:
            saved = json.loads(self.path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            saved = {}
        self.refresh()
        if isinstance(saved, dict):
            self.session_id = saved.get('session_id')
            saved_groups = saved.get('groups', {})
            for kind, group in self.groups.items():
                previous = saved_groups.get(kind, {}) if isinstance(saved_groups, dict) else {}
                if not isinstance(previous, dict):
                    continue
                rules = previous.get('rules', [])
                if not isinstance(rules, list) or not all(isinstance(r, dict) for r in rules):
                    continue
                signature = [{k: r.get(k) for k in ('id', 'threshold', 'reward', 'amount')} for r in rules]
                total = previous.get('total', 0)
                if (previous.get('enabled') == group['enabled'] and signature == group['rules']
                        and isinstance(total, int) and not isinstance(total, bool) and total >= 0
                        and group.get('remember', False)):
                    self.counters[kind] = total
                    self.completed[kind] = {r['id']: total // r['threshold'] for r in group['rules']}
        self.publish()

    def start_session(self, room_id):
        """A reconnect to the same TikTok room is still the same LIVE."""
        self.refresh()
        session_id = str(room_id) if room_id else None
        if session_id is None or session_id != self.session_id:
            for kind, group in self.groups.items():
                if not group.get('remember', False):
                    self.counters[kind] = 0
                    self.completed[kind] = {r['id']: 0 for r in group['rules']}
                    self.pending = deque(job for job in self.pending if job['kind'] != kind)
        self.session_id = session_id
        self.publish()

    def refresh(self):
        if self.config_path:
            try:
                stamp = self.config_path.stat().st_mtime_ns
                if stamp != self.stamp:
                    data = json.loads(self.config_path.read_text(encoding='utf-8-sig'))
                    settings(data)  # reject malformed edits as a whole
                    self.config['milestones'] = data.get('milestones', {})
                    self.stamp = stamp
            except (OSError, ValueError, TypeError):
                pass
        groups = settings(self.config)
        for kind, group in groups.items():
            old = self.groups.get(kind, {})
            if any(group.get(field) != old.get(field) for field in ('enabled', 'rules')):
                # Editing or toggling a group starts that group's new cycle.
                self.counters[kind] = 0
                self.completed[kind] = {rule['id']: 0 for rule in group['rules']}
                self.pending = deque(job for job in self.pending if job['kind'] != kind)
        changed = groups != self.groups
        self.groups = groups
        if changed:
            self.publish()

    def add(self, kind, count, name, key):
        self.refresh()
        group = self.groups[kind]
        if not group['enabled'] or count <= 0:
            return
        before = self.counters[kind]
        self.counters[kind] += int(count)
        for rule in group['rules']:
            crossings = self.counters[kind] // rule['threshold'] - before // rule['threshold']
            if crossings:
                self.completed[kind][rule['id']] += crossings
                self.pending.append({'kind': kind, 'reward': rule['reward'], 'remaining': crossings * rule['amount'], 'name': name, 'key': key})
        self.flush()
        self.publish()

    def flush(self):
        # Bounded work per tick, never discard a large combo or block the event loop.
        for _ in range(100):
            if not self.pending:
                break
            job = self.pending[0]
            try:
                self.send(self.config, job['reward'], job['name'], job['key'], '',
                          donation=job['kind'] == 'coins', notification_kind='gift' if job['kind'] == 'coins' else job['kind'])
            except OSError:
                break
            job['remaining'] -= 1
            if job['remaining'] == 0:
                self.pending.popleft()

    def publish(self):
        data = {'updated': time.time(), 'session_id': self.session_id, 'groups': {kind: {
            'enabled': group['enabled'], 'remember': group.get('remember', False), 'total': self.counters.get(kind, 0),
            'rules': [{**rule, 'current': self.counters.get(kind, 0) % rule['threshold'],
                       'completed': self.completed.get(kind, {}).get(rule['id'], 0)} for rule in group['rules']]
        } for kind, group in self.groups.items()}, 'pending': sum(job['remaining'] for job in self.pending)}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=self.path.parent, delete=False) as file:
                temporary = file.name
                json.dump(data, file, ensure_ascii=False)
            os.replace(temporary, self.path)
        except OSError:
            if temporary:
                try:
                    os.unlink(temporary)
                except OSError:
                    pass
