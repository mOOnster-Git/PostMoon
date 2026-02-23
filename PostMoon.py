# [모던_UI_라이브러리_시작]
import customtkinter as ctk
# (주의: standard tkinter는 messagebox나 filedialog 등 일부 기능에서만 제한적으로 사용합니다)
import tkinter as tk
from tkinter import filedialog, messagebox
# [모던_UI_라이브러리_종료]

import requests
import os
import json
import threading
import tempfile
import webbrowser
import subprocess
import re
from urllib.parse import urlparse

try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

# [모던_UI_테마설정_시작]
# 밝은 기본 테마로 설정 
ctk.set_appearance_mode("Light")  # "System", "Dark", "Light" 중 선택 가능
ctk.set_default_color_theme("blue")  # "blue", "green", "dark-blue"
# [모던_UI_테마설정_종료]

class PostMoonApp:
    def __init__(self, root):
        self.root = root
        self.VERSION = "v1.6.3 (KUTF Style Added)"
        self.root.title(f"PostMoon - AI Powered Rhymix Uploader {self.VERSION}")
        self.root.geometry("1200x800")
        
        self.chat_session = None 

        # [모던_UI_레이아웃_그리드_시작]
        self.root.grid_columnconfigure(0, weight=4)
        self.root.grid_columnconfigure(1, weight=6)
        self.root.grid_rowconfigure(0, weight=1)
        # [모던_UI_레이아웃_그리드_종료]

        self.setup_ui()
        self.load_config()

        if not HAS_GENAI:
            messagebox.showwarning("라이브러리 누락", "Google Generative AI 라이브러리가 없습니다.\n'pip install google-generativeai'를 실행해주세요.")

    def setup_ui(self):
        # ==========================================
        # [좌측_패널_시작] (원문 입력 및 AI 컨트롤)
        # ==========================================
        self.left_frame = ctk.CTkFrame(self.root, corner_radius=10)
        self.left_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="nsew")

        ctk.CTkLabel(self.left_frame, text="📝 원문 입력 (Raw Input)", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w", padx=15, pady=15)

        self.raw_text_entry = ctk.CTkTextbox(self.left_frame, wrap="word", font=ctk.CTkFont(size=13))
        self.raw_text_entry.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        ai_control_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        ai_control_frame.pack(fill="x", padx=15, pady=(0, 15))

        ctk.CTkLabel(ai_control_frame, text="출력 스타일 선택:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w")
        
        # [새로운 스타일 옵션 추가]
        self.style_combo = ctk.CTkComboBox(ai_control_frame, values=[
            '일반 텍스트 (Plain Text)', 
            'HTML 보도자료 스타일', 
            'HTML 국가대표 시범단 공지 스타일', 
            'HTML 세계줄넘기위원회 공지 스타일',
            'HTML KUTF 공식 홈페이지 스타일'
        ])
        self.style_combo.pack(fill="x", pady=(5, 10))

        self.ai_btn = ctk.CTkButton(ai_control_frame, text="✨ AI 분석 및 정리 (Gemini)", 
                                    command=self.process_with_ai_thread, 
                                    fg_color="#673ab7", hover_color="#512da8", height=40, font=ctk.CTkFont(size=14, weight="bold"))
        self.ai_btn.pack(fill="x")
        # [좌측_패널_종료]


        # ==========================================
        # [우측_패널_시작] (탭 뷰 구조 적용)
        # ==========================================
        self.right_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        self.right_frame.grid(row=0, column=1, padx=(0, 10), pady=(10, 5), sticky="nsew")
        
        self.tabview = ctk.CTkTabview(self.right_frame, corner_radius=10)
        self.tabview.pack(fill="both", expand=True)

        self.tab_result = self.tabview.add("🚀 결과 및 전송")
        self.tab_settings = self.tabview.add("⚙️ 설정 (Settings)")
        
        self.tabview.set("🚀 결과 및 전송")

        self.setup_result_tab()
        self.setup_settings_tab()
        # [우측_패널_종료]


        # ==========================================
        # [하단_푸터_시작]
        # ==========================================
        self.footer_frame = ctk.CTkFrame(self.root, height=30, corner_radius=0)
        self.footer_frame.grid(row=1, column=0, columnspan=2, sticky="ew")
        
        ctk.CTkLabel(self.footer_frame, text=f"PostMoon {self.VERSION} | 제작자 : mOOnster", font=ctk.CTkFont(size=11), text_color="gray").pack(side="right", padx=15)
        # [하단_푸터_종료]

        self.bind_context_menu(self.root)

    def setup_result_tab(self):
        parent = self.tab_result
        
        content_frame = ctk.CTkFrame(parent, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # 현재 타겟 라벨
        self.current_target_label = ctk.CTkLabel(
            content_frame, 
            text="현재 타겟: -", 
            font=ctk.CTkFont(size=13, weight="bold"), 
            text_color="#0056b3"
        )
        self.current_target_label.pack(anchor="w", pady=(0, 15))

        ctk.CTkLabel(content_frame, text="제목:").pack(anchor="w")
        self.title_entry = ctk.CTkEntry(content_frame, font=ctk.CTkFont(size=14))
        self.title_entry.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(content_frame, text="본문:").pack(anchor="w")
        self.content_text = ctk.CTkTextbox(content_frame, wrap="word", font=ctk.CTkFont(size=13))
        self.content_text.pack(fill="both", expand=True, pady=(0, 10))

        refine_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
        refine_frame.pack(fill="x", pady=5)
        
        self.refine_entry = ctk.CTkEntry(refine_frame, placeholder_text="AI에게 추가 수정 지시...")
        self.refine_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.refine_entry.bind("<Return>", lambda event: self.refine_with_ai_thread())

        self.refine_btn = ctk.CTkButton(refine_frame, text="🔄 이대로 수정", command=self.refine_with_ai_thread, width=100, fg_color="#ff9800", hover_color="#f57c00")
        self.refine_btn.pack(side="right")

        action_frame = ctk.CTkFrame(parent)
        action_frame.pack(fill="x", padx=10, pady=10)

        file_frame = ctk.CTkFrame(action_frame, fg_color="transparent")
        file_frame.pack(fill="x", padx=10, pady=10)

        self.selected_files = []
        self.file_btn = ctk.CTkButton(file_frame, text="📎 파일 선택", command=self.select_files, width=100)
        self.file_btn.pack(side="left")
        self.file_clear_btn = ctk.CTkButton(file_frame, text="🗑 선택된 파일 제거", command=self.clear_selected_files, width=140)
        self.file_clear_btn.pack(side="left", padx=(6, 6))
        self.file_label = ctk.CTkLabel(file_frame, text="선택된 파일 없음", text_color="gray")
        self.file_label.pack(side="left", padx=10)

        ctk.CTkButton(file_frame, text="🌐 HTML 미리보기", command=self.preview_html, width=120, fg_color="#17a2b8", hover_color="#138496").pack(side="right")

        btn_grid = ctk.CTkFrame(action_frame, fg_color="transparent")
        btn_grid.pack(fill="x", padx=10, pady=(0, 10))
        
        self.clear_btn = ctk.CTkButton(btn_grid, text="🗑️ 모두 지우기", command=self.clear_all_content, fg_color="#dc3545", hover_color="#c82333", height=45, font=ctk.CTkFont(size=14, weight="bold"))
        self.clear_btn.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        self.send_btn = ctk.CTkButton(btn_grid, text="📤 라이믹스로 전송", command=self.upload_to_rhymix_thread, fg_color="#007bff", hover_color="#0056b3", height=45, font=ctk.CTkFont(size=14, weight="bold"))
        self.send_btn.pack(side="right", fill="x", expand=True, padx=(5, 0))

    def setup_settings_tab(self):
        parent = self.tab_settings
        
        prof_frame = ctk.CTkFrame(parent)
        prof_frame.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkLabel(prof_frame, text="프로필 관리", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, columnspan=3, pady=(10,10), sticky="w", padx=10)
        
        self.profile_var = ctk.StringVar()
        self.profile_combo = ctk.CTkComboBox(prof_frame, variable=self.profile_var, command=self.on_profile_change, width=200)
        self.profile_combo.grid(row=1, column=0, padx=10, pady=(0, 10))
        
        ctk.CTkButton(prof_frame, text="➕ 추가", command=self.add_profile, width=60, fg_color="#28a745").grid(row=1, column=1, padx=5, pady=(0, 10))
        ctk.CTkButton(prof_frame, text="🗑️ 삭제", command=self.delete_profile, width=60, fg_color="#dc3545").grid(row=1, column=2, padx=5, pady=(0, 10))

        form_frame = ctk.CTkFrame(parent)
        form_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        form_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(form_frame, text="Rhymix 접속 설정", font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, columnspan=2, pady=15, sticky="w", padx=10)

        entries = [
            ("Rhymix URL:", "api_url_entry", False),
            ("Rhymix API Key:", "api_key_entry", True),
            ("Gemini API Key:", "gemini_key_entry", True)
        ]

        for i, (label_text, attr_name, is_password) in enumerate(entries):
            # mid가 들어갈 3번째 줄(row=3)을 비워두기 위한 줄바꿈 로직
            row = i + 1 if i < 2 else i + 2 
            ctk.CTkLabel(form_frame, text=label_text).grid(row=row, column=0, sticky="w", padx=10, pady=10)
            entry = ctk.CTkEntry(form_frame, show="*" if is_password else "")
            entry.grid(row=row, column=1, sticky="ew", padx=10, pady=10)
            setattr(self, attr_name, entry)

        # --- 게시판 ID (mid) 전용 콤보박스와 버튼 추가 ---
        ctk.CTkLabel(form_frame, text="게시판 선택 (Menu):").grid(row=3, column=0, sticky="w", padx=10, pady=10)
        
        mid_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        mid_frame.grid(row=3, column=1, sticky="ew", padx=10, pady=10)
        mid_frame.grid_columnconfigure(0, weight=1)
        self.menu_items_map = {}
        self.auto_apply_preset_on_load = False
        
        self.mid_entry = ctk.CTkComboBox(mid_frame, values=["직접 입력하거나 목록을 불러오세요"], command=self.on_mid_selected)
        self.mid_entry.grid(row=0, column=0, sticky="ew", padx=(0, 14), pady=(0, 6))
        
        self.fetch_mid_btn = ctk.CTkButton(mid_frame, text="🔄 사이트메뉴 불러오기", command=self.fetch_rhymix_menus_thread, width=150)
        self.fetch_mid_btn.grid(row=0, column=1, padx=(0, 6), pady=(0, 6))
        preset_btn_frame = ctk.CTkFrame(mid_frame, fg_color="transparent")
        preset_btn_frame.grid(row=1, column=1, sticky="e", padx=(0, 6), pady=(6, 0))
        self.add_preset_btn = ctk.CTkButton(preset_btn_frame, text="➕ 프리셋에 추가", width=120, command=self.add_current_mid_to_preset)
        self.add_preset_btn.grid(row=0, column=0, padx=(0, 8), pady=(0, 4))
        self.clear_preset_btn = ctk.CTkButton(preset_btn_frame, text="🗑 프리셋 초기화", width=120, command=self.clear_domain_preset)
        self.clear_preset_btn.grid(row=0, column=1, padx=(8, 0), pady=(0, 4))
        self.preset_switch = ctk.CTkSwitch(mid_frame, text="프리셋 적용", command=self.on_preset_switch)
        self.preset_switch.grid(row=2, column=1, sticky="e", padx=(0, 6), pady=(6, 0))

        ctk.CTkLabel(form_frame, text="분류 선택 (Category):").grid(row=4, column=0, sticky="w", padx=10, pady=10)
        cat_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        cat_frame.grid(row=4, column=1, sticky="ew", padx=10, pady=10)
        cat_frame.grid_columnconfigure(0, weight=1)
        self.category_entry = ctk.CTkComboBox(cat_frame, values=["게시판의 분류를 불러오세요"])
        self.category_entry.grid(row=0, column=0, sticky="ew", padx=(0, 14))
        self.fetch_cat_btn = ctk.CTkButton(cat_frame, text="🔄 분류 불러오기", command=self.fetch_rhymix_categories_thread, width=150)
        self.fetch_cat_btn.grid(row=0, column=1, padx=(0, 6))

        ctk.CTkButton(form_frame, text="💾 설정 저장", command=self.save_config_manual, height=40, font=ctk.CTkFont(weight="bold")).grid(row=5, column=0, columnspan=2, sticky="ew", padx=10, pady=20)

    # ==========================================
    # [데이터_처리_기능_시작]
    # ==========================================
    def bind_context_menu(self, widget):
        try:
            if isinstance(widget, (ctk.CTkEntry, ctk.CTkTextbox, tk.Entry, tk.Text)):
                widget.bind("<Button-3>", self.show_context_menu)
        except Exception:
            pass 
        if hasattr(widget, "winfo_children"):
            for child in widget.winfo_children():
                self.bind_context_menu(child)

    def show_context_menu(self, event):
        menu = tk.Menu(self.root, tearoff=0)
        widget = event.widget
        menu.add_command(label="잘라내기 (Cut)", command=lambda: widget.event_generate("<<Cut>>"))
        menu.add_command(label="복사 (Copy)", command=lambda: widget.event_generate("<<Copy>>"))
        menu.add_command(label="붙여넣기 (Paste)", command=lambda: widget.event_generate("<<Paste>>"))
        menu.add_separator()
        menu.add_command(label="모두 선택 (Select All)", command=lambda: self.select_all(widget))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def select_all(self, widget):
        try:
            if isinstance(widget, (ctk.CTkEntry, tk.Entry)):
                widget.select_range(0, tk.END)
                widget.icursor(tk.END)
            else:
                widget.tag_add("sel", "1.0", "end")
                widget.mark_set("insert", "1.0")
                widget.see("insert")
        except: pass
        return "break"

    def get_pure_mid(self):
        mid_raw = self.mid_entry.get().strip()
        match = re.search(r'\(([^)]+)\)$', mid_raw)
        return match.group(1).strip() if match else mid_raw

    def get_selected_category_srl(self):
        raw = self.category_entry.get().strip()
        m = re.search(r'\((\d+)\)$', raw)
        if m:
            try:
                return int(m.group(1))
            except:
                return 0
        try:
            return int(raw)
        except:
            return 0

    def update_summary_label(self):
        url = self.api_url_entry.get().strip()
        display_mid = self.mid_entry.get().strip()
        pure_mid = self.get_pure_mid()
        domain = "URL 미설정"
        if url:
            try:
                parsed = urlparse(url)
                domain = parsed.netloc if parsed.netloc else url
            except:
                domain = url
        if not display_mid or display_mid == "직접 입력하거나 목록을 불러오세요":
            display_mid = "mid 미설정"
        elif pure_mid and pure_mid in self.menu_items_map:
            display_mid = f"{self.menu_items_map[pure_mid]} ({pure_mid})"
        self.current_target_label.configure(text=f"현재 타겟: {domain} / {display_mid}")

    def get_config_path(self):
        home = os.path.expanduser("~")
        if os.name == 'nt':
             app_data = os.getenv('LOCALAPPDATA', os.path.join(home, 'AppData', 'Local'))
        else:
             app_data = os.path.join(home, '.config')
        config_dir = os.path.join(app_data, 'PostMoon')
        if not os.path.exists(config_dir):
            try: os.makedirs(config_dir)
            except Exception: return 'config.json'
        return os.path.join(config_dir, 'config.json')

    def load_config(self):
        self.profiles = {}
        self.current_profile = "Default"
        config_path = self.get_config_path()
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if 'api_url' in data and 'profiles' not in data:
                        self.profiles = {"Default": {'api_url': data.get('api_url', ''), 'api_key': data.get('api_key', ''), 'mid': data.get('mid', ''), 'gemini_api_key': data.get('gemini_api_key', '')}}
                        self.current_profile = "Default"
                    else:
                        self.profiles = data.get('profiles', {})
                        self.current_profile = data.get('last_used', 'Default')
            elif os.path.exists('config.json'):
                 try:
                    with open('config.json', 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        self.profiles = data.get('profiles', {})
                        self.current_profile = data.get('last_used', 'Default')
                 except: pass

            if not self.profiles:
                self.profiles = {"Default": {'api_url': "", 'api_key': "", 'mid': "", 'gemini_api_key': ""}}
                self.current_profile = "Default"

            self.update_profile_combo()
            self.load_profile_values()
            self.update_summary_label()
        except Exception:
            self.profiles = {"Default": {'api_url': "", 'api_key': "", 'mid': "", 'gemini_api_key': ""}}
            self.current_profile = "Default"
            self.update_profile_combo()

    def update_profile_combo(self):
        profile_names = list(self.profiles.keys())
        self.profile_combo.configure(values=profile_names)
        if self.current_profile in profile_names:
            self.profile_combo.set(self.current_profile)
        elif profile_names:
            self.profile_combo.set(profile_names[0])
            self.current_profile = profile_names[0]

    def load_profile_values(self):
        profile_data = self.profiles.get(self.current_profile, {})
        
        self.api_url_entry.delete(0, tk.END)
        self.api_url_entry.insert(0, profile_data.get('api_url', ''))
        
        self.api_key_entry.delete(0, tk.END)
        self.api_key_entry.insert(0, profile_data.get('api_key', ''))
        
        self.mid_entry.set(profile_data.get('mid', '직접 입력하거나 목록을 불러오세요'))
        
        self.gemini_key_entry.delete(0, tk.END)
        self.gemini_key_entry.insert(0, profile_data.get('gemini_api_key', ''))
        self.category_entry.set(str(profile_data.get('category_srl', '게시판의 분류를 불러오세요')))
        preset = self._get_domain_preset()
        if profile_data.get('preset_enabled', False):
            self.preset_switch.select()
            self.auto_apply_preset_on_load = True
            if profile_data.get('api_url') and profile_data.get('api_key'):
                try:
                    self.fetch_rhymix_menus_thread()
                except Exception:
                    pass
        else:
            self.preset_switch.deselect()
            self.auto_apply_preset_on_load = False

    def on_profile_change(self, choice):
        if choice:
            self.current_profile = choice
            self.load_profile_values()
            self.update_summary_label()
            self.save_config() 

    def add_profile(self):
        dialog = ctk.CTkInputDialog(text="새 프로필 이름을 입력하세요:", title="새 프로필")
        new_name = dialog.get_input()
        if new_name:
            if new_name in self.profiles:
                messagebox.showerror("오류", "이미 존재하는 프로필 이름입니다.")
                return
                
            self.profiles[new_name] = {
                'api_url': self.api_url_entry.get().strip(),
                'api_key': self.api_key_entry.get().strip(),
                'mid': self.get_pure_mid(),
                'gemini_api_key': self.gemini_key_entry.get().strip(),
                'category_srl': self.get_selected_category_srl(),
                'preset_enabled': bool(self.preset_switch.get()),
                'presets': {}
            }
            self.current_profile = new_name
            self.update_profile_combo()
            self.save_config()
            messagebox.showinfo("성공", f"프로필 '{new_name}'이 추가되었습니다.")

    def delete_profile(self):
        if len(self.profiles) <= 1:
            messagebox.showwarning("삭제 불가", "최소 하나의 프로필은 유지해야 합니다.")
            return
        target = self.current_profile
        if messagebox.askyesno("삭제 확인", f"정말로 프로필 '{target}'을 삭제하시겠습니까?"):
            del self.profiles[target]
            self.current_profile = list(self.profiles.keys())[0]
            self.update_profile_combo()
            self.load_profile_values()
            self.save_config()
            self.update_summary_label()

    def save_config(self):
        self.profiles[self.current_profile] = {
            'api_url': self.api_url_entry.get().strip(),
            'api_key': self.api_key_entry.get().strip(),
            'mid': self.get_pure_mid(),
            'gemini_api_key': self.gemini_key_entry.get().strip(),
            'category_srl': self.get_selected_category_srl(),
            'preset_enabled': bool(self.preset_switch.get()),
            'presets': self.profiles.get(self.current_profile, {}).get('presets', {})
        }
        config = {'profiles': self.profiles, 'last_used': self.current_profile}
        try:
            with open(self.get_config_path(), 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            self.update_summary_label()
        except Exception: pass

    def save_config_manual(self):
        self.save_config()
        messagebox.showinfo("저장 완료", "현재 프로필 설정이 저장되었습니다.")

    def select_files(self):
        files = filedialog.askopenfilenames()
        if files:
            self.selected_files = files
            self.file_label.configure(text=f"선택된 파일: {len(files)}개")
        else:
            self.selected_files = []
            self.file_label.configure(text="선택된 파일 없음")
    
    def clear_selected_files(self):
        self.selected_files = []
        self.file_label.configure(text="선택된 파일 없음")

    def preview_html(self):
        content = self.content_text.get("1.0", tk.END).strip()
        if not content:
            messagebox.showwarning("내용 없음", "미리보기할 본문 내용이 없습니다.")
            return
            
        html_content = f"""
        <!DOCTYPE html>
        <html lang="ko">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>PostMoon Preview</title>
            <style>body {{ font-family: 'Arial', sans-serif; padding: 20px; line-height: 1.6; }}</style>
        </head>
        <body>{content}</body>
        </html>
        """
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.html', mode='w', encoding='utf-8') as f:
                f.write(html_content)
                temp_path = f.name
                
            url = f'file://{temp_path}'
            
            browser_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
            ]
            
            opened = False
            for b_path in browser_paths:
                if os.path.exists(b_path):
                    subprocess.Popen([b_path, url])
                    opened = True
                    break
                    
            if not opened:
                webbrowser.open(url)
                
        except Exception as e:
            messagebox.showerror("미리보기 오류", f"브라우저를 여는 중 오류가 발생했습니다:\n{str(e)}")

    def process_with_ai_thread(self): threading.Thread(target=self.process_with_ai, daemon=True).start()
    
    def process_with_ai(self):
        if not HAS_GENAI:
            messagebox.showerror("오류", "google-generativeai 라이브러리가 필요합니다.\npip install google-generativeai")
            return

        gemini_key = self.gemini_key_entry.get().strip()
        raw_text = self.raw_text_entry.get("1.0", tk.END).strip()
        selected_style = self.style_combo.get()

        if not gemini_key: return messagebox.showwarning("설정 필요", "Gemini API Key를 입력해주세요.")
        if not raw_text: return messagebox.showwarning("입력 필요", "분석할 원문 텍스트를 입력해주세요.")

        self.ai_btn.configure(text="⏳ 분석 중...", state="disabled")
        
        try:
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel('gemini-flash-latest')

            # [KUTF 홈페이지 스타일에 대한 프롬프트 추가]
            style_instruction = ""
            if selected_style == 'HTML 보도자료 스타일':
                style_instruction = "- Use HTML formatting. Wrap body in <div class='press-release'>. Use <h2> and <p>."
            elif selected_style == 'HTML 국가대표 시범단 공지 스타일':
                style_instruction = "- Use HTML. Wrap body in <div class='notice-container' style='border: 2px solid #0056b3; padding: 20px; border-radius: 10px;'>. Use <h2 style='color: #0056b3; text-align: center;'>."
            elif selected_style == 'HTML 세계줄넘기위원회 공지 스타일':
                style_instruction = "- Use HTML. Wrap in <div style='max-width: 800px; padding: 20px;'>. End with a footer signature."
            elif selected_style == 'HTML KUTF 공식 홈페이지 스타일':
                style_instruction = """
                - Use HTML formatting.
                - Wrap the entire body in <div style='line-height: 1.6; color: #333; font-family: sans-serif;'>.
                - Use <h2 style='border-bottom: 2px solid #333; padding-bottom: 10px; margin-bottom: 20px;'> for the main heading (if needed inside the body).
                - Use <h3 style='border-left: 5px solid #333; padding-left: 10px; margin-top: 30px; margin-bottom: 10px;'> for section subtitles.
                - Wrap detailed descriptions or lists under subtitles in <div style='background-color: #f9f9f9; padding: 20px; border: 1px solid #eee; border-radius: 5px;'>.
                - Format lists inside boxes with <ul style='margin: 0; padding-left: 20px;'> and <li style='margin-bottom: 10px;'>.
                - Emphasize important keywords with <span style='color: #d9534f; font-weight: bold;'>.
                """
            else:
                style_instruction = "- Clean, clutter-free plain text. No HTML tags."

            prompt = f"""
            Task: Analyze text. Extract a 1-line title and clean body.
            Style Instructions: {style_instruction}
            Output Format:
            TITLE: [Title]
            BODY:
            [Body]
            Raw Text: {raw_text}
            """

            self.chat_session = model.start_chat(history=[])
            response = self.chat_session.send_message(prompt)
            self.parse_and_update_ui(response.text)
            self.save_config()

        except Exception as e:
            messagebox.showerror("AI 분석 오류", str(e))
        finally:
            self.root.after(0, lambda: self.ai_btn.configure(text="✨ AI 분석 및 정리 (Gemini)", state="normal"))

    def refine_with_ai_thread(self): threading.Thread(target=self.refine_with_ai, daemon=True).start()

    def refine_with_ai(self):
        if not self.chat_session: return messagebox.showwarning("오류", "먼저 AI 분석을 실행해주세요.")
        instruction = self.refine_entry.get().strip()
        if not instruction: return messagebox.showwarning("입력 필요", "수정할 내용을 입력해주세요.")

        self.refine_btn.configure(text="⏳ 수정 중...", state="disabled")
        try:
            prompt = f"User Instruction: {instruction}\nRewrite Title and Body in the EXACT same format as before."
            response = self.chat_session.send_message(prompt)
            self.parse_and_update_ui(response.text)
            self.root.after(0, lambda: self.refine_entry.delete(0, tk.END))
        except Exception as e:
            messagebox.showerror("AI 수정 오류", str(e))
        finally:
            self.root.after(0, lambda: self.refine_btn.configure(text="🔄 이대로 수정", state="normal"))

    def parse_and_update_ui(self, result_text):
        title, body, is_body = "", [], False
        for line in result_text.split('\n'):
            if line.startswith("TITLE:"): title = line.replace("TITLE:", "").strip()
            elif line.startswith("BODY:"): is_body = True
            elif is_body: body.append(line)
        
        self.root.after(0, self.update_ui_result, title, "\n".join(body).strip())

    def update_ui_result(self, title, body):
        self.title_entry.delete(0, tk.END)
        self.title_entry.insert(0, title)
        self.content_text.delete("1.0", tk.END)
        self.content_text.insert("1.0", body)
        self.tabview.set("🚀 결과 및 전송") # 결과창으로 포커스 이동

    def fetch_rhymix_menus_thread(self):
        threading.Thread(target=self.fetch_rhymix_menus, daemon=True).start()
        
    def fetch_rhymix_menus(self):
        api_url = self.api_url_entry.get().strip()
        api_key = self.api_key_entry.get().strip()
        
        if not api_url or not api_key:
            return messagebox.showwarning("입력 필요", "Rhymix URL과 API Key를 먼저 입력해주세요.")
            
        self.fetch_mid_btn.configure(text="⏳ 불러오는 중...", state="disabled")
        headers = {"Authorization": f"Bearer {api_key}", "X-Api-Key": api_key}
        data = {"action": "get_menu_list", "writable_only": 1}
        
        try:
            response = requests.post(api_url, headers=headers, data=data)
            if response.status_code == 200:
                result = response.json()
                if result.get('error') == 0 and 'menu_list' in result:
                    menu_items = result['menu_list']
                    combo_values = []
                    preset = self._get_domain_preset()
                    if bool(self.preset_switch.get()) and preset and preset.get('include_mids'):
                        include = set(preset['include_mids'])
                        for item in menu_items:
                            self.menu_items_map[item['mid']] = item['item_name']
                            if item['mid'] in include:
                                combo_values.append(f"{item['item_name']} ({item['mid']})")
                    else:
                        for item in menu_items:
                            self.menu_items_map[item['mid']] = item['item_name']
                            combo_values.append(f"{item['item_name']} ({item['mid']})")
                    if not combo_values:
                        combo_values = ["연결된 게시판 메뉴가 없습니다"]
                        
                    self.root.after(0, lambda: self.mid_entry.configure(values=combo_values))
                    self.root.after(0, lambda: self.mid_entry.set(combo_values[0]))
                    if bool(self.preset_switch.get()):
                        try:
                            self.apply_domain_preset()
                        except Exception:
                            pass
                    self.root.after(0, self.fetch_rhymix_categories_thread)
                else:
                    messagebox.showerror("실패", "메뉴를 불러오지 못했습니다.")
            else:
                messagebox.showerror("오류", f"서버 오류: {response.status_code}")
        except Exception as e:
            messagebox.showerror("네트워크 오류", str(e))
        finally:
            self.root.after(0, lambda: self.fetch_mid_btn.configure(text="🔄 사이트메뉴 불러오기", state="normal"))

    def on_mid_selected(self, choice):
        try:
            self.fetch_rhymix_categories_thread()
        except Exception:
            pass
        try:
            self.update_summary_label()
        except Exception:
            pass

    def on_preset_switch(self):
        self.apply_domain_preset()
        self.save_config()

    def _get_current_domain(self):
        url = self.api_url_entry.get().strip()
        try:
            return urlparse(url).netloc.lower()
        except:
            return ""

    def _get_domain_preset(self):
        profile = self.profiles.get(self.current_profile, {})
        presets = profile.get('presets', {})
        domain = self._get_current_domain()
        return presets.get(domain, {})

    def apply_domain_preset_thread(self):
        threading.Thread(target=self.apply_domain_preset, daemon=True).start()

    def apply_domain_preset(self):
        values = list(self.mid_entry.cget("values"))
        preset = self._get_domain_preset()
        include = preset.get('include_mids')
        if not include:
            return
        include_set = set(include)
        filtered = []
        for v in values:
            m = re.search(r'\(([^)]+)\)$', v)
            mid = m.group(1) if m else v
            if mid in include_set:
                filtered.append(v)
        if filtered:
            self.root.after(0, lambda: self.mid_entry.configure(values=filtered))
            self.root.after(0, lambda: self.mid_entry.set(filtered[0]))

    def add_current_mid_to_preset(self):
        mid = self.get_pure_mid()
        domain = self._get_current_domain()
        profile = self.profiles.get(self.current_profile, {})
        presets = profile.get('presets', {})
        preset = presets.get(domain, {})
        include = preset.get('include_mids', [])
        if mid and mid not in include:
            include.append(mid)
        preset['include_mids'] = include
        presets[domain] = preset
        profile['presets'] = presets
        self.profiles[self.current_profile] = profile
        self.save_config()

    def clear_domain_preset(self):
        domain = self._get_current_domain()
        profile = self.profiles.get(self.current_profile, {})
        presets = profile.get('presets', {})
        if domain in presets:
            presets[domain] = {'include_mids': []}
        profile['presets'] = presets
        self.profiles[self.current_profile] = profile
        self.preset_switch.deselect()
        self.save_config()

    def fetch_rhymix_categories_thread(self):
        threading.Thread(target=self.fetch_rhymix_categories, daemon=True).start()

    def fetch_rhymix_categories(self):
        api_url = self.api_url_entry.get().strip()
        api_key = self.api_key_entry.get().strip()
        mid = self.get_pure_mid()
        if not api_url or not api_key or not mid:
            return messagebox.showwarning("입력 필요", "Rhymix URL, API Key, 게시판을 먼저 설정하세요.")
        self.fetch_cat_btn.configure(text="⏳ 불러오는 중...", state="disabled")
        headers = {"Authorization": f"Bearer {api_key}", "X-Api-Key": api_key}
        data = {"action": "get_board_categories", "mid": mid}
        try:
            response = requests.post(api_url, headers=headers, data=data)
            if response.status_code == 200:
                result = response.json()
                if result.get('error') == 0 and 'categories' in result:
                    values = []
                    for c in result['categories']:
                        values.append(f"{c['title']} ({c['category_srl']})")
                    if not values:
                        values = ["분류 없음"]
                    self.root.after(0, lambda: self.category_entry.configure(values=values))
                    self.root.after(0, lambda: self.category_entry.set(values[0]))
                    self.root.after(0, lambda: self.save_config())
                else:
                    messagebox.showerror("실패", "분류를 불러오지 못했습니다.")
            else:
                messagebox.showerror("오류", f"서버 오류: {response.status_code}")
        except Exception as e:
            messagebox.showerror("네트워크 오류", str(e))
        finally:
            self.root.after(0, lambda: self.fetch_cat_btn.configure(text="🔄 분류 불러오기", state="normal"))

    def upload_to_rhymix_thread(self): threading.Thread(target=self.upload_to_rhymix, daemon=True).start()

    def upload_to_rhymix(self):
        api_url = re.sub(r'\s+', '', self.api_url_entry.get())
        api_key = self.api_key_entry.get().strip()
        mid = self.get_pure_mid()
        title = self.title_entry.get().strip()
        content = self.content_text.get("1.0", tk.END).strip()
        category_srl = self.get_selected_category_srl()
        
        if not all([api_url, api_key, mid, title]):
            return messagebox.showwarning("입력 오류", "URL, API Key, 게시판, 제목을 입력해주세요.")

        if 'HTML' not in self.style_combo.get(): content = content.replace('\n', '<br />')
        
        def _is_image(path):
            return str(path).lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg'))

        has_image = any(_is_image(p) for p in (self.selected_files or []))
        if not content and not has_image:
            return messagebox.showwarning("입력 오류", "본문을 입력하거나 이미지 파일을 첨부해주세요.")

        headers = {"Authorization": f"Bearer {api_key}", "X-Api-Key": api_key}
        data = {"api_key": api_key, "action": "create_document", "mid": mid, "title": title, "content": content}
        if category_srl:
            data["category_srl"] = category_srl
        files_to_send, open_files = [], []

        try:
            if self.selected_files:
                for file_path in self.selected_files:
                    if os.path.exists(file_path):
                        f = open(file_path, 'rb')
                        open_files.append(f)
                        files_to_send.append(('file[]', (os.path.basename(file_path), f, 'application/octet-stream')))
            
            self.root.after(0, lambda: self.send_btn.configure(text="전송 중...", state="disabled"))
            response = requests.post(api_url, headers=headers, data=data, files=files_to_send)
            
            if response.status_code >= 400:
                return messagebox.showerror("전송 실패", f"서버 오류: {response.text[:200]}")
            
            result = response.json()
            if result.get('success') or result.get('error') == 0:
                messagebox.showinfo("성공", "게시글이 성공적으로 전송되었습니다.")
            else:
                messagebox.showerror("실패", f"전송 실패: {result.get('message', '알 수 없는 오류')}")
                
        except Exception as e:
            messagebox.showerror("오류", f"네트워크 오류 발생:\n{str(e)}")
        finally:
            for f in open_files: f.close()
            self.root.after(0, lambda: self.send_btn.configure(text="📤 라이믹스로 전송", state="normal"))

    def clear_all_content(self):
        if messagebox.askyesno("초기화", "작성 중인 내용을 모두 지우시겠습니까?"):
            self.selected_files = []
            self.file_label.configure(text="선택된 파일 없음")
            self.raw_text_entry.delete("1.0", tk.END)
            self.title_entry.delete(0, tk.END)
            self.content_text.delete("1.0", tk.END)
            self.refine_entry.delete(0, tk.END)
    # [데이터_처리_기능_종료]

if __name__ == "__main__":
    app_root = ctk.CTk()
    app = PostMoonApp(app_root)
    app_root.mainloop()
