import os
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

from kivy.config import Config
Config.set('kivy', 'window_icon', '')

from kivy.lang import Builder
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.utils import platform
from kivy.animation import Animation

from kivymd.app import MDApp
from kivymd.uix.list import OneLineListItem, ThreeLineListItem
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.dialog import MDDialog
from kivymd.uix.snackbar import Snackbar

from app.backend.database import DatabaseManager
from app.backend.ai_providers import LocalAIAgent, OnlineAIAgent
from app.backend.connectivity import ConnectivityMonitor, is_online
from app.backend.persona import cyber_persona, postprocess_response
from app.backend.scanner import DeviceScanner
from app.backend.scheduler import ScanScheduler

KV_PATH = os.path.join(os.path.dirname(__file__), 'ui', 'cybersentinel.kv')


class CyberSentinelAIApp(MDApp):
    db: DatabaseManager
    local_ai: LocalAIAgent
    online_ai: OnlineAIAgent
    scanner: DeviceScanner
    scheduler: ScanScheduler
    connectivity: ConnectivityMonitor

    def build(self):
        self.title = 'CyberSentinel AI'
        self.theme_cls.theme_style = 'Dark'
        self.theme_cls.primary_palette = 'Teal'

        # Ensure directories
        base_dir = self.user_data_dir
        os.makedirs(base_dir, exist_ok=True)
        os.makedirs(os.path.join(base_dir, 'logs'), exist_ok=True)

        # Database
        self.db = DatabaseManager(os.path.join(base_dir, 'cybersentinel.db'))

        # Persona
        persona = cyber_persona('Analyst')
        self.local_ai = LocalAIAgent(persona, kb_path=os.path.join(base_dir, 'kb.json'))
        self.online_ai = OnlineAIAgent(persona)

        # Scanner and scheduler
        self.scanner = DeviceScanner(base_dir)
        self.scheduler = ScanScheduler(self._scheduled_scan)

        # Connectivity
        self.connectivity = ConnectivityMonitor()
        self.connectivity.start(self._on_connectivity_change)

        # Load UI
        return Builder.load_file(KV_PATH)

    # UI event handlers
    def on_start(self):
        Clock.schedule_once(lambda _dt: self._load_recent_history(), 0.3)
        # Start scheduled scans if enabled
        interval = float(self.db.get_setting('SCAN_INTERVAL_MIN', 60))
        if interval and interval > 0:
            self.scheduler.set_interval_minutes(interval)
            self.scheduler.start()

    def on_send_message(self):
        screen = self.root
        chat_input = screen.ids.tabs.get_tab_list()[0].content.ids.chat_input
        text = (chat_input.text or '').strip()
        if not text:
            return
        chat_input.text = ''
        session_id = 'default'

        # Persist user message
        self.db.add_chat_message(session_id, 'user', text, {"ts": datetime.utcnow().isoformat()})
        self._append_chat_bubble(text, sender='user')
        self._start_avatar_pulse()

        # Respond asynchronously
        threading.Thread(target=self._answer_async, args=(text, session_id), daemon=True).start()

    def _append_chat_bubble(self, text: str, sender: str):
        chat_list = self.root.ids.tabs.get_tab_list()[0].content.ids.chat_list
        bubble = MDCard(size_hint_y=None, padding=dp(12), radius=[12,12,12,12])
        bubble.md_bg_color = (0.09, 0.12, 0.15, 1) if sender == 'bot' else (0.05, 0.2, 0.12, 1)
        label = MDLabel(text=text, theme_text_color='Custom', text_color=(0.8,0.95,1,1))
        label.size_hint_y = None
        label.height = label.texture_size[1]
        bubble.add_widget(label)
        chat_list.add_widget(bubble)
        Clock.schedule_once(lambda _dt: self._scroll_chat_to_end(), 0.05)

    def _scroll_chat_to_end(self):
        chat_scroll = self.root.ids.tabs.get_tab_list()[0].content.ids.chat_scroll
        chat_scroll.scroll_y = 0

    def _start_avatar_pulse(self):
        try:
            avatar = self.root.ids.chat_tab.ids.avatar_card
            anim = Animation(opacity=0.6, duration=0.2) + Animation(opacity=1.0, duration=0.2)
            anim.repeat = True
            # Auto-stop after short delay to avoid infinite loop
            anim.start(avatar)
            Clock.schedule_once(lambda _dt: anim.stop(avatar), 1.2)
        except Exception:
            pass

    def _answer_async(self, question: str, session_id: str):
        try:
            # Decide offline or online
            answer_text: Optional[str] = None
            meta: Dict[str, Any] = {}
            if is_online():
                # Prefer online using available keys
                openai_key = self.db.get_setting('OPENAI_API_KEY')
                hf_key = self.db.get_setting('HUGGINGFACE_API_KEY')
                try:
                    if openai_key:
                        answer_text, meta = self.online_ai.answer_with_openai(openai_key, question)
                    elif hf_key:
                        answer_text, meta = self.online_ai.answer_with_hf(hf_key, question)
                except Exception:
                    answer_text = None
            if answer_text is None:
                # Offline
                answer_text, meta = self.local_ai.answer(question)
                if not is_online():
                    # Queue for later learning
                    self.db.enqueue_unanswered(question)
            # Postprocess
            answer_text = postprocess_response(answer_text)
            # Persist and display
            self.db.add_chat_message(session_id, 'bot', answer_text, meta)
            Clock.schedule_once(lambda _dt, t=answer_text: self._append_chat_bubble(t, 'bot'))
        except Exception as e:
            Clock.schedule_once(lambda _dt: Snackbar(text=f'Error: {e}').open())

    def on_start_scan(self):
        if self.scanner.is_scanning():
            Snackbar(text='Scan already running').open()
            return

        card = self.root.ids.tabs.get_tab_list()[1].content.ids.scan_card
        progress_bar = card.ids.scan_progress
        status_label = card.ids.scan_status
        progress_bar.value = 0
        status_label.text = 'Starting scan…'

        scan_id = self.db.add_scan_log('running', {"progress": 0})

        def on_progress(p: float, label: str):
            Clock.schedule_once(lambda _dt: self._update_scan_ui(progress_bar, status_label, p, label))

        def on_complete(findings: Dict[str, Any]):
            self.db.update_scan_log(scan_id, status='completed', findings=findings, ended_at=datetime.utcnow().isoformat())
            Clock.schedule_once(lambda _dt: self._finish_scan_ui(progress_bar, status_label, findings))
            Clock.schedule_once(lambda _dt: self._reload_scan_history(), 0.2)

        self.scanner.start_scan(on_progress=on_progress, on_complete=on_complete)

    def _update_scan_ui(self, progress_bar, status_label, p: float, label: str):
        progress_bar.value = int(p * 100)
        status_label.text = f'{label} ({int(p*100)}%)'

    def _finish_scan_ui(self, progress_bar, status_label, findings: Dict[str, Any]):
        progress_bar.value = 100
        status_label.text = f"Completed • Threat score: {findings.get('threat_score', 0):.2f}"

    def _reload_scan_history(self):
        lst = self.root.ids.tabs.get_tab_list()[1].content.ids.scan_history_list
        lst.clear_widgets()
        scans = self.db.get_recent_scans(20)
        for s in scans:
            started = s.get('started_at') or ''
            ended = s.get('ended_at') or ''
            status = s.get('status')
            threat = s.get('findings', {}).get('threat_score', 0)
            item = ThreeLineListItem(text=f"{status} • score {threat:.2f}", secondary_text=f"Start: {started}", tertiary_text=f"End: {ended}")
            lst.add_widget(item)

    def _load_recent_history(self):
        # Populate chat history recent
        hist_list = self.root.ids.tabs.get_tab_list()[2].content.ids.history_list
        hist_list.clear_widgets()
        chats = self.db.get_recent_chats(30)
        for c in chats:
            timestamp = c.get('created_at', '')
            sender = c.get('sender', '')
            msg = c.get('message', '')
            text = f"{sender}: {msg[:60]}" + ("…" if len(msg) > 60 else "")
            hist_list.add_widget(ThreeLineListItem(text=text, secondary_text=timestamp, tertiary_text=c.get('session_id', 'default')))
        # Populate scans
        self._reload_scan_history()

    def on_save_settings(self):
        screen = self.root
        settings_tab = screen.ids.tabs.get_tab_list()[3].content
        openai_key = settings_tab.ids.openai_key.text.strip()
        hf_key = settings_tab.ids.hf_key.text.strip()
        interval_text = settings_tab.ids.scan_interval.text.strip() or '60'
        try:
            interval = float(interval_text)
        except Exception:
            interval = 60.0
        if openai_key:
            self.db.set_setting('OPENAI_API_KEY', openai_key)
        if hf_key:
            self.db.set_setting('HUGGINGFACE_API_KEY', hf_key)
        self.db.set_setting('SCAN_INTERVAL_MIN', interval)
        if interval and interval > 0:
            self.scheduler.set_interval_minutes(interval)
            if not self.scheduler.is_running():
                self.scheduler.start()
        else:
            self.scheduler.stop()
        Snackbar(text='Settings saved').open()

    def _scheduled_scan(self):
        # Only auto-run if not already scanning
        if not self.scanner.is_scanning():
            self.on_start_scan()

    def _on_connectivity_change(self, online: bool):
        if online:
            # Attempt to resolve unanswered queue
            pending = self.db.get_pending_unanswered(20)
            for item in pending:
                qid = item['id']
                question = item['question']
                try:
                    openai_key = self.db.get_setting('OPENAI_API_KEY')
                    hf_key = self.db.get_setting('HUGGINGFACE_API_KEY')
                    answer_text: Optional[str] = None
                    meta: Dict[str, Any] = {}
                    if openai_key:
                        answer_text, meta = self.online_ai.answer_with_openai(openai_key, question)
                    elif hf_key:
                        answer_text, meta = self.online_ai.answer_with_hf(hf_key, question)
                    if answer_text:
                        answer_text = postprocess_response(answer_text)
                        self.db.mark_unanswered_answered(qid, answer_text)
                        # Learn locally
                        self.local_ai.kb.learn(question, answer_text)
                        # Append to chat and history
                        self.db.add_chat_message('default', 'bot', answer_text, meta)
                except Exception:
                    continue


if __name__ == '__main__':
    CyberSentinelAIApp().run()