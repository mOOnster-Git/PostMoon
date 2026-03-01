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
import html
from datetime import datetime
from urllib.parse import urlparse

try:
    from tkcalendar import Calendar
    HAS_TKCALENDAR = True
except ImportError:
    HAS_TKCALENDAR = False

import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

# [모던_UI_테마설정_시작]
# 밝은 기본 테마로 설정 
ctk.set_appearance_mode("System")  # "System", "Dark", "Light" 중 선택 가능
ctk.set_default_color_theme("blue")  # "blue", "green", "dark-blue"
# [모던_UI_테마설정_종료]

class PostMoonApp:
    def __init__(self, root):
        self.root = root
        self.VERSION = "v2.0.0"
        self.root.title(f"PostMoon - AI Powered Rhymix Uploader {self.VERSION}")
        self.root.geometry("1100x800")
        self.root.minsize(900, 650)
        
        self.chat_session = None 

        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=0)
        self.root.grid_rowconfigure(2, weight=0)

        self.setup_ui()
        self.load_config()

        if not HAS_GENAI:
            messagebox.showwarning("라이브러리 누락", "Google Generative AI 라이브러리가 없습니다.\n'pip install google-generativeai'를 실행해주세요.")

    def setup_ui(self):
        # ── 숨김 설정 위젯 (load/save 호환) ─────────────────────
        self._create_hidden_settings_widgets()

        # ── 전체 탭뷰 ────────────────────────────────────────────
        self.tabview = ctk.CTkTabview(
            self.root, corner_radius=10,
            fg_color=("#f0f0f0", "#1a1b24"),
            segmented_button_fg_color=("#d8dae6", "#121320"),
            segmented_button_selected_color=("#1e50c8", "#2563eb"),
            segmented_button_selected_hover_color=("#1640a8", "#1d4ed8"),
            segmented_button_unselected_color=("#d8dae6", "#1a1c2e"),
            segmented_button_unselected_hover_color=("#c4c6d6", "#1e2040"),
            text_color=("#222", "#e0e0e0"),
            text_color_disabled=("#888", "#666")
        )
        self.tabview.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        # 탭 버튼 폰트·높이·모서리 강화
        try:
            self.tabview._segmented_button.configure(
                font=ctk.CTkFont(size=13, weight="bold"),
                height=46,
                corner_radius=8,
                border_width=2,
                border_color=("#c0c2d0", "#0e0f1a"),
            )
        except Exception:
            pass

        self.tab_raw   = self.tabview.add("✏️  원문 입력")
        self.tab_post  = self.tabview.add("📝  게시글 편집")
        self.tab_popup = self.tabview.add("🪟  팝업 설정")
        self.tabview.set("✏️  원문 입력")

        self.setup_raw_tab()
        self.setup_post_tab()
        self.setup_popup_tab()

        # ── 하단 액션 바 ──────────────────────────────────────────
        ab = ctk.CTkFrame(self.root, corner_radius=0, fg_color=("#d0d2da", "#111318"), height=64)
        ab.grid(row=1, column=0, sticky="ew")
        ab.grid_columnconfigure(1, weight=1)
        ab.grid_propagate(False)

        self.clear_btn = ctk.CTkButton(
            ab, text="🗑️  모두 지우기", command=self.clear_all_content,
            fg_color=("#7a3a3a", "#5c2a2a"), hover_color=("#5c2a2a", "#3e1a1a"),
            height=44, font=ctk.CTkFont(size=14, weight="bold"), corner_radius=6, width=150
        )
        self.clear_btn.grid(row=0, column=0, padx=(14, 6), pady=10)

        self.current_target_label = ctk.CTkLabel(
            ab, text="현재 타겟: -",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("#555", "#9aa0b0"), anchor="center"
        )
        self.current_target_label.grid(row=0, column=1, padx=8)

        ctk.CTkButton(
            ab, text="⚙️  설정", command=self.open_settings_modal,
            fg_color=("#5a6475", "#2e3242"), hover_color=("#474e5e", "#232838"),
            height=44, font=ctk.CTkFont(size=13, weight="bold"), corner_radius=6, width=110
        ).grid(row=0, column=2, padx=(6, 6), pady=10)

        self.send_btn = ctk.CTkButton(
            ab, text="📤  라이믹스로 최종 전송",
            command=self.upload_to_rhymix_thread,
            fg_color=("#2d5a8e", "#1a3a5f"), hover_color=("#1e4070", "#102840"),
            height=44, font=ctk.CTkFont(size=14, weight="bold"), corner_radius=6, width=230
        )
        self.send_btn.grid(row=0, column=3, padx=(6, 14), pady=10)

        # ── 하단 푸터 ─────────────────────────────────────────────
        self.footer_frame = ctk.CTkFrame(self.root, height=28, corner_radius=0, fg_color=("#3d4451", "#1e2130"))
        self.footer_frame.grid(row=2, column=0, sticky="ew")
        ctk.CTkLabel(
            self.footer_frame,
            text=f"PostMoon {self.VERSION}  |  AI Powered Rhymix Uploader  |  mOOnster",
            font=ctk.CTkFont(size=11), text_color=("#c0c5cf", "#9aa0b0"), anchor="center"
        ).pack(side="left", expand=True, fill="x", padx=16)

        self.bind_context_menu(self.root)

    def _create_hidden_settings_widgets(self):
        """load_config/save_config 호환용 숨김 위젯 (화면에 표시되지 않음)"""
        hf = ctk.CTkFrame(self.root)  # 배치 안 함 → 보이지 않음
        self.profile_var = ctk.StringVar()
        self.profile_combo = ctk.CTkComboBox(hf, variable=self.profile_var,
                                             command=self.on_profile_change, width=200)
        self.api_url_entry = ctk.CTkEntry(hf)
        self.api_key_entry = ctk.CTkEntry(hf)
        self.gemini_key_entry = ctk.CTkEntry(hf)
        self.menu_items_map = {}
        self.auto_apply_preset_on_load = False
        self.mid_entry = ctk.CTkComboBox(hf,
                                         values=["직접 입력하거나 목록을 불러오세요"],
                                         command=self.on_mid_selected)
        self.preset_switch = ctk.CTkSwitch(hf, text="프리셋 적용", command=self.on_preset_switch)
        self.category_entry = ctk.CTkComboBox(hf, values=["게시판의 분류를 불러오세요"])
        self.add_preset_btn = ctk.CTkButton(hf, text="➕ 프리셋에 추가",
                                            command=self.add_current_mid_to_preset)
        self.clear_preset_btn = ctk.CTkButton(hf, text="🗑 프리셋 초기화",
                                              command=self.clear_domain_preset)
        self.fetch_mid_btn = ctk.CTkButton(hf, text="🔄 사이트메뉴 불러오기",
                                           command=self.fetch_rhymix_menus_thread)
        self.fetch_cat_btn = ctk.CTkButton(hf, text="🔄 분류 불러오기",
                                           command=self.fetch_rhymix_categories_thread)

    def setup_raw_tab(self):
        parent = self.tab_raw
        parent.grid_rowconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=0)
        parent.grid_columnconfigure(0, weight=1)

        self.raw_text_entry = ctk.CTkTextbox(
            parent, wrap="word", font=ctk.CTkFont(size=13), corner_radius=8,
            fg_color=("#ffffff", "#252836"), border_width=1, border_color=("#c8cad4", "#3d4160")
        )
        self.raw_text_entry.grid(row=0, column=0, sticky="nsew", padx=20, pady=(16, 8))

        ac = ctk.CTkFrame(parent, corner_radius=8, fg_color=("#e0e2e8", "#1e2130"))
        ac.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 16))
        ac.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            ac, text="출력 스타일", width=80, anchor="w",
            font=ctk.CTkFont(size=12, weight="bold"), text_color=("#444", "#aaa")
        ).grid(row=0, column=0, padx=(14, 6), pady=12)

        self.style_combo = ctk.CTkComboBox(ac, values=[
            '일반 텍스트 (Plain Text)',
            'HTML 보도자료 스타일',
            'HTML 국가대표 시범단 공지 스타일',
            'HTML 세계줄넘기위원회 공지 스타일',
            'HTML KUTF 공식 홈페이지 스타일'
        ], font=ctk.CTkFont(size=12), height=36,
           fg_color=("#ffffff", "#252836"), border_color=("#c8cad4", "#3d4160"))
        self.style_combo.grid(row=0, column=1, sticky="ew", padx=(0, 12), pady=12)

        self.ai_btn = ctk.CTkButton(
            ac, text="✨  AI 분석 및 정리 (Gemini)",
            command=self.process_with_ai_thread,
            fg_color=("#4b5563", "#374151"), hover_color=("#374151", "#1f2937"),
            height=44, font=ctk.CTkFont(size=14, weight="bold"), corner_radius=8, width=250
        )
        self.ai_btn.grid(row=0, column=2, padx=(0, 12), pady=8)

    def setup_post_tab(self):
        parent = self.tab_post
        parent.grid_rowconfigure(2, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        # 헤더 (게시글 편집 타이틀 + 미리보기)
        hr = ctk.CTkFrame(parent, corner_radius=0, fg_color=("#3d4451", "#1e2130"), height=46)
        hr.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        hr.grid_propagate(False)
        hr.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            hr, text="📝  게시글 편집",
            font=ctk.CTkFont(size=14, weight="bold"), text_color="#e0e0e0"
        ).grid(row=0, column=0, padx=16, sticky="w")
        self.post_preview_btn = ctk.CTkButton(
            hr, text="🌐 미리보기", command=self.preview_html,
            width=110, height=30, fg_color=("#5a6475", "#2e3242"),
            hover_color=("#474e5e", "#232838"), corner_radius=6, font=ctk.CTkFont(size=12)
        )
        self.post_preview_btn.grid(row=0, column=2, padx=(0, 12), pady=8)

        # 제목
        tf = ctk.CTkFrame(parent, fg_color="transparent")
        tf.grid(row=1, column=0, sticky="ew", padx=20, pady=(12, 6))
        tf.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(tf, text="제목", width=44, anchor="w",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=("#333", "#ccc")).grid(row=0, column=0)
        self.title_entry = ctk.CTkEntry(tf, font=ctk.CTkFont(size=14), corner_radius=7, height=38,
                                        fg_color=("#ffffff", "#252836"), border_color=("#c8cad4", "#3d4160"))
        self.title_entry.grid(row=0, column=1, sticky="ew", padx=(6, 0))

        # 본문
        self.content_text = ctk.CTkTextbox(
            parent, wrap="word", font=ctk.CTkFont(size=13), corner_radius=8,
            fg_color=("#ffffff", "#252836"), border_width=1, border_color=("#c8cad4", "#3d4160")
        )
        self.content_text.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 6))

        # AI 수정
        rf = ctk.CTkFrame(parent, fg_color="transparent")
        rf.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 6))
        rf.grid_columnconfigure(0, weight=1)
        self.refine_entry = ctk.CTkEntry(
            rf, placeholder_text="AI 추가 수정 지시사항 입력 후 Enter 또는 버튼 클릭...",
            corner_radius=7, height=36,
            fg_color=("#ffffff", "#252836"), border_color=("#c8cad4", "#3d4160")
        )
        self.refine_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.refine_entry.bind("<Return>", lambda event: self.refine_with_ai_thread())
        self.refine_btn = ctk.CTkButton(
            rf, text="🔄 AI 수정", command=self.refine_with_ai_thread,
            width=110, height=36, fg_color=("#4b5563", "#374151"),
            hover_color=("#374151", "#1f2937"), corner_radius=7
        )
        self.refine_btn.grid(row=0, column=1)

        # 파일 첨부
        ff = ctk.CTkFrame(parent, fg_color=("#e4e4e4", "#1e2030"), corner_radius=8)
        ff.grid(row=4, column=0, sticky="ew", padx=20, pady=(0, 16))
        ff.grid_columnconfigure(3, weight=1)
        ctk.CTkLabel(ff, text="📎 첨부", width=50, anchor="w",
                     font=ctk.CTkFont(size=12, weight="bold"),
                     text_color=("#333", "#ccc")).grid(row=0, column=0, padx=(12, 4), pady=8)
        self.selected_files = []
        self.file_btn = ctk.CTkButton(
            ff, text="파일 선택", command=self.select_files,
            width=80, height=28, corner_radius=6, font=ctk.CTkFont(size=12)
        )
        self.file_btn.grid(row=0, column=1, padx=(0, 6), pady=6)
        self.file_clear_btn = ctk.CTkButton(
            ff, text="제거", command=self.clear_selected_files,
            width=50, height=28, corner_radius=6, font=ctk.CTkFont(size=12),
            fg_color="gray", hover_color="#555"
        )
        self.file_clear_btn.grid(row=0, column=2, padx=(0, 8), pady=6)
        self.file_label = ctk.CTkLabel(
            ff, text="선택된 파일 없음", text_color="gray", font=ctk.CTkFont(size=11)
        )
        self.file_label.grid(row=0, column=3, padx=4, sticky="w")

    def setup_popup_tab(self):
        parent = self.tab_popup
        parent.grid_rowconfigure(5, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        # 헤더
        ph = ctk.CTkFrame(parent, corner_radius=0, fg_color=("#3d4451", "#1e2130"), height=46)
        ph.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        ph.grid_propagate(False)
        ph.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            ph, text="🪟  팝업 설정",
            font=ctk.CTkFont(size=14, weight="bold"), text_color="#e0e0e0"
        ).grid(row=0, column=0, padx=16, sticky="w")
        self.create_popup_var = tk.StringVar(value="N")
        self.create_popup_check = ctk.CTkCheckBox(
            ph, text="등록 활성화",
            variable=self.create_popup_var, onvalue="Y", offvalue="N",
            font=ctk.CTkFont(size=12, weight="bold"), text_color="#e0e0e0",
            hover_color="#5a6475", border_color="#8a90a0", checkmark_color="#e0e0e0"
        )
        self.create_popup_check.grid(row=0, column=1, padx=16, sticky="w")
        self.create_popup_check.deselect()
        ctk.CTkButton(
            ph, text="🪟 미리보기", command=self.preview_popup,
            width=100, height=30, fg_color=("#5a6475", "#2e3242"),
            hover_color=("#474e5e", "#232838"), corner_radius=6, font=ctk.CTkFont(size=12)
        ).grid(row=0, column=2, padx=(0, 12))

        # 설정 카드 (노출위치 + 날짜 + 숨김/폭)
        sg = ctk.CTkFrame(parent, fg_color=("#e4e4e4", "#1e2030"), corner_radius=8)
        sg.grid(row=1, column=0, sticky="ew", padx=20, pady=(14, 6))
        sg.grid_columnconfigure(1, weight=1)
        sg.grid_columnconfigure(4, weight=1)

        ctk.CTkLabel(
            sg, text="노출위치", font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("#444", "#bbb")
        ).grid(row=0, column=0, padx=(14, 6), pady=10, sticky="w")
        self.popup_scope_combo = ctk.CTkSegmentedButton(
            sg, values=["현재 게시판", "전체 페이지", "메인 인덱스"], font=ctk.CTkFont(size=11)
        )
        self.popup_scope_combo.grid(row=0, column=1, columnspan=4, sticky="ew", padx=(0, 14), pady=8)
        self.popup_scope_combo.set("메인 인덱스")  # 기본값: 메인 인덱스
        self.popup_index_module_srl = 0
        self.popup_index_mid = ""

        # 날짜 행 - 시작일/종료일 프레임으로 묶어서 버튼을 입력칸 바로 옆에 배치
        date_row = ctk.CTkFrame(sg, fg_color="transparent")
        date_row.grid(row=1, column=0, columnspan=6, sticky="ew", padx=(14, 14), pady=(0, 8))

        ctk.CTkLabel(date_row, text="시작일", font=ctk.CTkFont(size=11),
                     text_color=("#555", "#aaa")).pack(side="left", padx=(0, 4))
        self.popup_start_entry = ctk.CTkEntry(
            date_row, width=110, placeholder_text="비워두면 제한없음",
            font=ctk.CTkFont(size=11), height=30, corner_radius=6,
            fg_color=("#ffffff", "#252836"), border_color=("#c8cad4", "#3d4160")
        )
        self.popup_start_entry.pack(side="left")
        ctk.CTkButton(
            date_row, text="📅", width=28, height=28, corner_radius=6,
            command=lambda: self.open_date_picker(self.popup_start_entry)
        ).pack(side="left", padx=(2, 20))

        ctk.CTkLabel(date_row, text="종료일", font=ctk.CTkFont(size=11),
                     text_color=("#555", "#aaa")).pack(side="left", padx=(0, 4))
        self.popup_end_entry = ctk.CTkEntry(
            date_row, width=110, placeholder_text="비워두면 제한없음",
            font=ctk.CTkFont(size=11), height=30, corner_radius=6,
            fg_color=("#ffffff", "#252836"), border_color=("#c8cad4", "#3d4160")
        )
        self.popup_end_entry.pack(side="left")
        ctk.CTkButton(
            date_row, text="📅", width=28, height=28, corner_radius=6,
            command=lambda: self.open_date_picker(self.popup_end_entry)
        ).pack(side="left", padx=(2, 0))

        ctk.CTkLabel(sg, text="숨김(일)", font=ctk.CTkFont(size=11),
                     text_color=("#555", "#aaa")).grid(row=2, column=0, padx=(14, 4), pady=(0, 10), sticky="w")
        self.popup_cookie_days_entry = ctk.CTkEntry(
            sg, width=60, font=ctk.CTkFont(size=11), height=30, corner_radius=6,
            fg_color=("#ffffff", "#252836"), border_color=("#c8cad4", "#3d4160")
        )
        self.popup_cookie_days_entry.grid(row=2, column=1, padx=(0, 4), pady=(0, 8), sticky="w")
        self.popup_cookie_days_entry.insert(0, "1")
        ctk.CTkLabel(sg, text="폭(px)", font=ctk.CTkFont(size=11),
                     text_color=("#555", "#aaa")).grid(row=2, column=3, padx=(0, 4), pady=(0, 10), sticky="w")
        self.popup_width_entry = ctk.CTkEntry(
            sg, width=80, font=ctk.CTkFont(size=11), height=30, corner_radius=6,
            fg_color=("#ffffff", "#252836"), border_color=("#c8cad4", "#3d4160")
        )
        self.popup_width_entry.grid(row=2, column=4, padx=(0, 4), pady=(0, 8), sticky="w")
        self.popup_width_entry.insert(0, "400")

        # AI 지시 + 생성/수정
        ctk.CTkLabel(
            parent, text="  AI 지시사항 (내용에 맞는 버튼 문구 자동 생성)",
            font=ctk.CTkFont(size=11), text_color=("gray", "#7a7fb5")
        ).grid(row=2, column=0, padx=20, pady=(6, 2), sticky="w")
        au = ctk.CTkFrame(parent, fg_color="transparent")
        au.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 8))
        au.grid_columnconfigure(0, weight=1)
        self.popup_ai_entry = ctk.CTkComboBox(au, values=[
            "간략하고 명확한 3줄 요약 (기본)",
            "행사/일정/장소 강조 안내",
            "모집 대상/기간/방법 중심 요약",
            "공지사항 주요 핵심만 알림"
        ], font=ctk.CTkFont(size=11), height=34, corner_radius=7,
           fg_color=("#ffffff", "#252836"), border_color=("#c8cad4", "#3d4160"))
        self.popup_ai_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.popup_ai_entry.set("간략하고 명확한 3줄 요약 (기본)")
        self.popup_ai_entry.bind("<Return>", lambda event: self.refine_popup_with_ai_thread())
        self.popup_ai_btn = ctk.CTkButton(
            au, text="✨ 생성", width=80, height=34, corner_radius=7,
            fg_color=("#4b5563", "#374151"), hover_color=("#374151", "#1f2937"),
            command=self.generate_popup_with_ai_thread
        )
        self.popup_ai_btn.grid(row=0, column=1, padx=(0, 6))
        self.popup_ai_refine_btn = ctk.CTkButton(
            au, text="🔄 재수정", width=90, height=34, corner_radius=7,
            fg_color=("#4b5563", "#374151"), hover_color=("#374151", "#1f2937"),
            command=self.refine_popup_with_ai_thread
        )
        self.popup_ai_refine_btn.grid(row=0, column=2)

        ctk.CTkLabel(
            parent, text="  ① AI 생성  →  ② 내용 확인  →  ③ 미리보기  →  ④ 전송",
            font=ctk.CTkFont(size=10), text_color=("gray", "#7a7fb5")
        ).grid(row=4, column=0, padx=20, pady=(0, 4), sticky="w")

        self.popup_content_text = ctk.CTkTextbox(
            parent, wrap="word", font=ctk.CTkFont(size=12), corner_radius=8,
            fg_color=("#ffffff", "#252836"), border_width=1, border_color=("#c8cad4", "#3d4160")
        )
        self.popup_content_text.grid(row=5, column=0, sticky="nsew", padx=20, pady=(0, 16))

    def open_settings_modal(self):
        win = tk.Toplevel(self.root)
        win.title("⚙️ 환경 설정")
        win.geometry("580x680")
        win.resizable(False, True)
        win.transient(self.root)
        win.grab_set()

        scroll = ctk.CTkScrollableFrame(win, corner_radius=0, fg_color=("#f0f0f0", "#1e1f2e"))
        scroll.pack(fill="both", expand=True)
        scroll.grid_columnconfigure(1, weight=1)

        # ── 프로필 관리 ──────────────────────────────────────────
        ctk.CTkLabel(
            scroll, text="프로필 관리", font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=0, column=0, columnspan=3, sticky="w", padx=16, pady=(16, 6))

        pr = ctk.CTkFrame(scroll, fg_color="transparent")
        pr.grid(row=1, column=0, columnspan=3, sticky="ew", padx=16, pady=(0, 12))
        pr.grid_columnconfigure(0, weight=1)

        m_profile_var = ctk.StringVar(value=self.profile_var.get())
        m_profile_combo = ctk.CTkComboBox(
            pr, variable=m_profile_var, width=200,
            values=list(self.profiles.keys()) if self.profiles else ["Default"]
        )
        m_profile_combo.grid(row=0, column=0, sticky="w")

        def _add_profile():
            name = ctk.CTkInputDialog(text="새 프로필 이름:", title="프로필 추가").get_input()
            if name and name.strip():
                name = name.strip()
                self.profiles[name] = {"api_url": "", "api_key": "", "mid": "", "gemini_api_key": ""}
                self.current_profile = name
                vals = list(self.profiles.keys())
                self.profile_combo.configure(values=vals)
                self.profile_combo.set(name)
                m_profile_combo.configure(values=vals)
                m_profile_var.set(name)
                _apply_profile_to_modal(name)

        def _delete_profile():
            name = m_profile_var.get()
            if len(self.profiles) <= 1:
                messagebox.showwarning("경고", "마지막 프로필은 삭제할 수 없습니다.", parent=win)
                return
            if name in self.profiles:
                del self.profiles[name]
            vals = list(self.profiles.keys())
            new_name = vals[0] if vals else "Default"
            self.current_profile = new_name
            self.profile_combo.configure(values=vals)
            self.profile_combo.set(new_name)
            m_profile_combo.configure(values=vals)
            m_profile_var.set(new_name)
            _apply_profile_to_modal(new_name)

        ctk.CTkButton(pr, text="➕ 추가", command=_add_profile,
                      width=70, fg_color=("#2e6e3e", "#1a4a28")).grid(row=0, column=1, padx=(8, 4))
        ctk.CTkButton(pr, text="🗑️ 삭제", command=_delete_profile,
                      width=70, fg_color=("#7a3a3a", "#5c2a2a")).grid(row=0, column=2, padx=(4, 0))

        # ── 접속 설정 폼 ──────────────────────────────────────────
        ctk.CTkLabel(
            scroll, text="Rhymix 접속 설정", font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=2, column=0, columnspan=3, sticky="w", padx=16, pady=(4, 6))

        lbl_conf = [("Rhymix URL", False), ("Rhymix API Key", True), ("Gemini API Key", True)]
        m_entries = {}
        for i, (lbl, pw) in enumerate(lbl_conf):
            ctk.CTkLabel(scroll, text=lbl+":",
                         font=ctk.CTkFont(size=12), text_color=("#444", "#bbb")).grid(
                row=3+i, column=0, sticky="w", padx=16, pady=6)
            e = ctk.CTkEntry(scroll, show="*" if pw else "", height=34, corner_radius=6)
            e.grid(row=3+i, column=1, columnspan=2, sticky="ew", padx=(6, 16), pady=6)
            m_entries[lbl] = e

        # ── 게시판 mid ───────────────────────────────────────────
        ctk.CTkLabel(scroll, text="게시판 mid:",
                     font=ctk.CTkFont(size=12), text_color=("#444", "#bbb")).grid(
            row=6, column=0, sticky="w", padx=16, pady=6)
        mid_r = ctk.CTkFrame(scroll, fg_color="transparent")
        mid_r.grid(row=6, column=1, columnspan=2, sticky="ew", padx=(6, 16), pady=6)
        mid_r.grid_columnconfigure(0, weight=1)
        m_mid = ctk.CTkComboBox(mid_r, values=self.mid_entry.cget("values"))
        m_mid.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkButton(mid_r, text="🔄 불러오기", width=110,
                      command=lambda: self._fetch_menus_and_update_modal(m_mid)).grid(row=0, column=1)

        # 프리셋 관리
        p_row = ctk.CTkFrame(scroll, fg_color="transparent")
        p_row.grid(row=7, column=0, columnspan=3, sticky="ew", padx=16, pady=(0, 6))
        m_preset_switch = ctk.CTkSwitch(p_row, text="프리셋 적용", command=self.on_preset_switch)
        m_preset_switch.pack(side="left", padx=(0, 12))
        ctk.CTkButton(p_row, text="➕ 프리셋 추가", width=110,
                      command=self.add_current_mid_to_preset).pack(side="left", padx=(0, 6))
        ctk.CTkButton(p_row, text="🗑 프리셋 초기화", width=110,
                      command=self.clear_domain_preset).pack(side="left")

        # ── 분류 category ─────────────────────────────────────────
        ctk.CTkLabel(scroll, text="분류 category:",
                     font=ctk.CTkFont(size=12), text_color=("#444", "#bbb")).grid(
            row=8, column=0, sticky="w", padx=16, pady=6)
        cat_r = ctk.CTkFrame(scroll, fg_color="transparent")
        cat_r.grid(row=8, column=1, columnspan=2, sticky="ew", padx=(6, 16), pady=6)
        cat_r.grid_columnconfigure(0, weight=1)
        m_cat = ctk.CTkComboBox(cat_r, values=self.category_entry.cget("values"))
        m_cat.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ctk.CTkButton(cat_r, text="🔄 불러오기", width=110,
                      command=self.fetch_rhymix_categories_thread).grid(row=0, column=1)

        # ── 프로필 전환 시 폼 채우기 ───────────────────────────────
        def _apply_profile_to_modal(name):
            if not name:
                name = m_profile_var.get()
            if name in self.profiles:
                p = self.profiles[name]
                m_entries["Rhymix URL"].delete(0, tk.END)
                m_entries["Rhymix URL"].insert(0, p.get("api_url", ""))
                m_entries["Rhymix API Key"].delete(0, tk.END)
                m_entries["Rhymix API Key"].insert(0, p.get("api_key", ""))
                m_entries["Gemini API Key"].delete(0, tk.END)
                m_entries["Gemini API Key"].insert(0, p.get("gemini_api_key", ""))
                m_mid.set(p.get("mid", "직접 입력하거나 목록을 불러오세요"))
                cat_val = p.get("category_srl", "")
                m_cat.set(str(cat_val) if cat_val else "게시판의 분류를 불러오세요")
                if p.get("preset_enabled", False):
                    m_preset_switch.select()
                else:
                    m_preset_switch.deselect()

        m_profile_combo.configure(command=_apply_profile_to_modal)
        _apply_profile_to_modal(m_profile_var.get())

        # ── 저장 ─────────────────────────────────────────────────
        def _save_and_close():
            name = m_profile_var.get()
            if not name:
                return
            if name not in self.profiles:
                self.profiles[name] = {}
            self.profiles[name]["api_url"]         = m_entries["Rhymix URL"].get().strip()
            self.profiles[name]["api_key"]         = m_entries["Rhymix API Key"].get().strip()
            self.profiles[name]["gemini_api_key"]  = m_entries["Gemini API Key"].get().strip()
            self.profiles[name]["mid"]             = m_mid.get().strip()
            cat_raw = m_cat.get().strip()
            _m = re.search(r'\((\d+)\)$', cat_raw)
            self.profiles[name]["category_srl"] = (
                int(_m.group(1)) if _m else (int(cat_raw) if cat_raw.isdigit() else 0)
            )
            self.profiles[name]["preset_enabled"] = (m_preset_switch.get() == 1)
            self.current_profile = name
            # 숨김 위젯 동기화
            self.api_url_entry.delete(0, tk.END)
            self.api_url_entry.insert(0, self.profiles[name]["api_url"])
            self.api_key_entry.delete(0, tk.END)
            self.api_key_entry.insert(0, self.profiles[name]["api_key"])
            self.gemini_key_entry.delete(0, tk.END)
            self.gemini_key_entry.insert(0, self.profiles[name]["gemini_api_key"])
            self.mid_entry.set(self.profiles[name]["mid"])
            self.update_profile_combo()
            self.save_config_manual()
            win.destroy()

        ctk.CTkButton(
            scroll, text="💾  설정 저장 및 닫기",
            command=_save_and_close,
            height=46, font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=("#2d5a8e", "#1a3a5f"), hover_color=("#1e4070", "#102840"),
            corner_radius=8
        ).grid(row=9, column=0, columnspan=3, sticky="ew", padx=16, pady=(12, 20))

    def _fetch_menus_and_update_modal(self, m_mid_widget):
        """설정 모달에서 메뉴 목록 불러오기"""
        def _thread():
            self.fetch_rhymix_menus()
            vals = self.mid_entry.cget("values")
            self.root.after(0, lambda: m_mid_widget.configure(values=vals))
        threading.Thread(target=_thread, daemon=True).start()

    def setup_result_tab(self):
        pass  # 구버전 호환 스텁

    def setup_settings_tab(self):
        pass  # 구버전 호환 스텁


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

    def normalize_popup_date(self, date_text):
        text = (date_text or "").strip()
        if not text:
            return ""
        if re.match(r'^\d{4}-\d{2}-\d{2}$', text):
            return text
        if re.match(r'^\d{8}$', text):
            return f"{text[:4]}-{text[4:6]}-{text[6:8]}"
        return ""

    def get_popup_scope_value(self):
        selected = self.popup_scope_combo.get().strip()
        if "전체" in selected:
            return "all"
        if "인덱스" in selected:
            return "index"
        return "current"

    def open_url_in_browser(self, url):
        browser_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
        ]

        for b_path in browser_paths:
            if os.path.exists(b_path):
                subprocess.Popen([b_path, url])
                return True

        return webbrowser.open(url)

    def open_date_picker(self, target_entry):
        if not HAS_TKCALENDAR:
            messagebox.showinfo("안내", "달력 위젯이 설치되지 않았습니다.\n`pip install tkcalendar` 후 사용해주세요.")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("날짜 선택")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)

        init_date = self.normalize_popup_date(target_entry.get().strip()) or datetime.now().strftime("%Y-%m-%d")
        try:
            year, month, day = [int(x) for x in init_date.split('-')]
        except Exception:
            now = datetime.now()
            year, month, day = now.year, now.month, now.day

        cal = Calendar(dialog, selectmode='day', year=year, month=month, day=day, date_pattern='yyyy-mm-dd')
        cal.pack(padx=10, pady=10)

        btn_row = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_row.pack(fill="x", padx=10, pady=(0, 10))

        def _apply():
            target_entry.delete(0, tk.END)
            target_entry.insert(0, cal.get_date())
            dialog.destroy()

        ctk.CTkButton(btn_row, text="확인", width=80, command=_apply).pack(side="right", padx=(6, 0))
        ctk.CTkButton(btn_row, text="취소", width=80, command=dialog.destroy, fg_color="gray").pack(side="right")

    def _infer_btn_text(self, title):
        t = (title or "").lower()
        if any(k in t for k in ["모집", "지원", "신청", "접수"]):
            return "신청 / 지원하러 가기 >"
        if any(k in t for k in ["행사", "대회", "경기", "시합", "선발전"]):
            return "행사 상세 보기 >"
        if any(k in t for k in ["결과", "순위", "성적", "우승"]):
            return "결과 확인하러 가기 >"
        if any(k in t for k in ["공지", "안내", "알림", "유의사항"]):
            return "공지사항 확인하러 가기 >"
        if any(k in t for k in ["일정", "스케줄", "계획"]):
            return "일정 확인하러 가기 >"
        return "자세히 보기 >"

    def build_simplified_popup_content(self, title, content):
        source = content or ""
        source = re.sub(r'(?i)<br\s*/?>', '\n', source)
        source = re.sub(r'(?i)</p\s*>', '\n', source)
        source = re.sub(r'(?i)</li\s*>', '\n', source)
        source = re.sub(r'<[^>]+>', ' ', source)
        source = html.unescape(source)

        lines = []
        for raw_line in source.splitlines():
            clean = re.sub(r'\s+', ' ', raw_line).strip(" -•\t")
            if clean:
                lines.append(clean)

        normalized_title = re.sub(r'\s+', '', (title or '').lower())
        if normalized_title:
            lines = [line for line in lines if re.sub(r'\s+', '', line.lower()) != normalized_title]

        if not lines:
            lines = ["핵심 안내사항을 확인해주세요."]

        lines = lines[:3]
        highlight = lines[0]
        rest_lines = lines[1:] if len(lines) > 1 else []
        list_items = "".join([f"<li style='margin-bottom: 6px;'>{html.escape(line)}</li>" for line in rest_lines])
        title_html = f"<h2 style='margin:0 0 14px 0; font-size:18px; font-weight:800; color:#111; line-height:1.3; border-bottom:2px solid #e2e2e2; padding-bottom:10px;'>{html.escape(title)}</h2>" if title else ""

        return f"""
        <div style='font-family: Arial, sans-serif; line-height: 1.6; color: #222; padding: 25px; box-sizing: border-box;'>
            {title_html}
            <div style='background:#f7f7f7; border:1px solid #e2e2e2; border-radius:10px; padding:14px;'>
                <p style='margin:0 0 10px 0; font-size:15px; font-weight:700; color:#1565d8;'>{html.escape(highlight)}</p>
                <ul style='margin:0; padding-left:18px; color:#444;'>{list_items}</ul>
            </div>
            <div style='text-align:center; margin-top:16px;'>
              <a href='#' style='display:inline-block; background:#3b5bdb; color:#fff; text-decoration:none; padding:11px 28px; border-radius:999px; font-size:14px; font-weight:700;'>{html.escape(self._infer_btn_text(title))}</a>
            </div>
        </div>
        """.strip()

    def get_popup_content_text(self):
        try:
            return self.popup_content_text.get("1.0", tk.END).strip()
        except Exception:
            return ""

    def set_popup_content_text(self, text):
        try:
            self.popup_content_text.delete("1.0", tk.END)
            self.popup_content_text.insert("1.0", (text or "").strip())
        except Exception:
            pass

    def generate_popup_with_ai_thread(self):
        threading.Thread(target=self.generate_popup_with_ai, daemon=True).start()

    def refine_popup_with_ai_thread(self):
        threading.Thread(target=self.refine_popup_with_ai, daemon=True).start()

    def generate_popup_with_ai(self):
        title = self.title_entry.get().strip()
        content = self.content_text.get("1.0", tk.END).strip()
        instruction = self.popup_ai_entry.get().strip()
        if not title:
            return messagebox.showwarning("입력 필요", "팝업 AI 생성을 위해 제목을 입력해주세요.")
        if not content:
            return messagebox.showwarning("입력 필요", "팝업 AI 생성을 위해 본문을 입력해주세요.")

        if not HAS_GENAI or not self.gemini_key_entry.get().strip():
            self.set_popup_content_text(self.build_simplified_popup_content(title, content))
            return messagebox.showinfo("안내", "Gemini 설정이 없어 기본 간략 팝업으로 생성했습니다.")

        self.popup_ai_btn.configure(text="생성 중...", state="disabled")
        try:
            genai.configure(api_key=self.gemini_key_entry.get().strip())
            model = genai.GenerativeModel('gemini-flash-latest')
            prompt = f"""
            You are creating a concise popup body HTML only.
            Goal: users should understand 핵심 내용 at a glance.
            Rules:
            - Include the post title as a prominent heading (<h2>) at the very top of the content, styled naturally with the popup body.
            - 1 highlighted key sentence (bold, colored) below the title + up to 2 short bullet points.
            - No markdown, return HTML body only.
            - Compact card style with inline CSS, wrapped in <div style="padding:25px; box-sizing:border-box;">.
            - AUTOMATICALLY infer a short context-appropriate CTA button label from the post title/content (e.g. "신청하러 가기 >", "결과 확인 >", "행사 상세 보기 >", "공지 확인 >").
            - End with a centered styled button: <div style='text-align:center; margin-top:16px;'><a href='#' style='display:inline-block; background:#3b5bdb; color:#fff; text-decoration:none; padding:11px 28px; border-radius:999px; font-size:14px; font-weight:700;'>[ inferred CTA text ]</a></div>
            Extra Instruction: {instruction or '핵심만, 짧고 눈에 띄게'}
            Post Title: {title}
            Post Body: {content}
            """
            response = model.generate_content(prompt)
            ai_html = (response.text or "").strip()
            if not ai_html:
                ai_html = self.build_simplified_popup_content(title, content)
            self.root.after(0, lambda: self.set_popup_content_text(ai_html))
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "quota" in err_str.lower() or "RESOURCE_EXHAUSTED" in err_str:
                self.root.after(0, lambda: messagebox.showerror(
                    "팝업 AI 오류",
                    "Gemini API 요청 한도(Quota) 초과\n\n"
                    "무료 플랜의 분당 요청 횟수 제한에 도달했습니다.\n"
                    "잠시 후(10~30초) 다시 시도해주세요.\n\n"
                    "반복 발생 시: https://ai.google.dev/gemini-api/docs/rate-limits"
                ))
            else:
                fallback = self.build_simplified_popup_content(title, content)
                self.root.after(0, lambda: self.set_popup_content_text(fallback))
        finally:
            self.root.after(0, lambda: self.popup_ai_btn.configure(text="✨ 팝업AI 생성", state="normal"))

    def refine_popup_with_ai(self):
        current_popup = self.get_popup_content_text()
        title = self.title_entry.get().strip()
        instruction = self.popup_ai_entry.get().strip()
        if not current_popup:
            return messagebox.showwarning("입력 필요", "먼저 팝업AI 생성 또는 수동 입력을 해주세요.")
        if not instruction:
            return messagebox.showwarning("입력 필요", "재수정 지시를 입력해주세요.")

        if not HAS_GENAI or not self.gemini_key_entry.get().strip():
            return messagebox.showwarning("설정 필요", "팝업 재수정은 Gemini API Key가 필요합니다.")

        self.popup_ai_refine_btn.configure(text="수정 중...", state="disabled")
        try:
            genai.configure(api_key=self.gemini_key_entry.get().strip())
            model = genai.GenerativeModel('gemini-flash-latest')
            prompt = f"""
            Rewrite popup HTML body by instruction.
            Rules:
            - Keep it concise and visually clear.
            - Do NOT add a title heading.
            - Keep 1 highlighted sentence and short bullets.
            - Return HTML body only.
            Post Title: {title}
            Current Popup HTML: {current_popup}
            User Instruction: {instruction}
            """
            response = model.generate_content(prompt)
            ai_html = (response.text or "").strip()
            if ai_html:
                self.root.after(0, lambda: self.set_popup_content_text(ai_html))
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "quota" in err_str.lower() or "RESOURCE_EXHAUSTED" in err_str:
                msg = ("Gemini API 요청 한도(Quota) 초과\n\n"
                       "잠시 후(10~30초) 다시 시도해주세요.\n\n"
                       "반복 발생 시: https://ai.google.dev/gemini-api/docs/rate-limits")
            else:
                msg = err_str
            self.root.after(0, lambda m=msg: messagebox.showerror("팝업 AI 오류", m))
        finally:
            self.root.after(0, lambda: self.popup_ai_refine_btn.configure(text="🔄 재수정", state="normal"))

    def collect_popup_payload(self, title, content):
        start_norm = self.normalize_popup_date(self.popup_start_entry.get())
        end_norm = self.normalize_popup_date(self.popup_end_entry.get())

        if self.popup_start_entry.get().strip() and not start_norm:
            messagebox.showwarning("입력 오류", "팝업 시작일 형식이 올바르지 않습니다. YYYY-MM-DD 로 입력해주세요.")
            return None
        if self.popup_end_entry.get().strip() and not end_norm:
            messagebox.showwarning("입력 오류", "팝업 종료일 형식이 올바르지 않습니다. YYYY-MM-DD 로 입력해주세요.")
            return None
        if start_norm and end_norm and end_norm < start_norm:
            messagebox.showwarning("입력 오류", "팝업 종료일은 시작일보다 빠를 수 없습니다.")
            return None

        cookie_days_raw = self.popup_cookie_days_entry.get().strip() or "1"
        try:
            cookie_days = int(cookie_days_raw)
        except Exception:
            messagebox.showwarning("입력 오류", "숨김일은 숫자로 입력해주세요.")
            return None
        cookie_days = max(1, min(cookie_days, 365))

        width_raw = self.popup_width_entry.get().strip() or "400"
        try:
            popup_width = int(width_raw)
        except Exception:
            messagebox.showwarning("입력 오류", "팝업 폭은 숫자로 입력해주세요.")
            return None
        popup_width = max(280, min(popup_width, 1200))

        popup_content = self.get_popup_content_text() or self.build_simplified_popup_content(title, content)
        if not self.get_popup_content_text():
            self.set_popup_content_text(popup_content)
        popup_mode = self.get_popup_scope_value()
        if popup_mode == "index" and not int(self.popup_index_module_srl or 0):
            messagebox.showwarning("입력 필요", "메인 인덱스 페이지 정보를 먼저 불러와야 합니다. 설정 탭에서 사이트메뉴를 다시 불러오세요.")
            return None

        return {
            "create_popup": "Y",
            "popup_scope": self.get_popup_scope_value(),
            "popup_target_mode": popup_mode,
            "popup_target_module_srl": str(int(self.popup_index_module_srl or 0)) if popup_mode == "index" else "",
            "popup_start_date": start_norm,
            "popup_end_date": end_norm,
            "popup_cookie_days": str(cookie_days),
            "popup_width": str(popup_width),
            "popup_content": popup_content
        }

    def preview_popup(self):
        title = self.title_entry.get().strip()
        content = self.content_text.get("1.0", tk.END).strip()
        if not title:
            return messagebox.showwarning("입력 필요", "팝업 미리보기를 위해 제목을 입력해주세요.")
        if not content:
            return messagebox.showwarning("입력 필요", "팝업 미리보기를 위해 본문을 입력해주세요.")

        payload = self.collect_popup_payload(title, content)
        if not payload:
            return

        safe_title = html.escape(title if title else "공지")

        popup_content = payload.get("popup_content", "")
        # 버튼 자동생성: 이미 <a> 태그가 없는 경우에만 추가
        if "<a href=" not in popup_content:
            auto_btn = self._infer_btn_text(title)
            popup_content += f"<div style='text-align:center; margin-top:16px;'><a href='#' style='display:inline-block; background:#3b5bdb; color:#fff; text-decoration:none; padding:11px 28px; border-radius:999px; font-size:14px; font-weight:700;'>{html.escape(auto_btn)}</a></div>" 
        try:
            popup_width = int(payload.get("popup_width", "400"))
        except Exception:
            popup_width = 560

        html_content = f"""
        <!DOCTYPE html>
        <html lang=\"ko\">
        <head>
            <meta charset=\"UTF-8\" />
            <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
            <title>Popup Preview</title>
            <style>
                body {{ margin: 0; font-family: Arial, sans-serif; background: #f0f2f5; }}
                .overlay {{ min-height: 100vh; display: flex; align-items: flex-start; justify-content: center; padding-top: 80px; }}
                .popup-manager-popup {{ width: {popup_width}px; max-width: calc(100vw - 40px); background: #fff; border: 1px solid #ddd; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15); border-radius: 8px; overflow: hidden; }}
                .popup-manager-content {{ max-height: 70vh; overflow-y: auto; line-height: 1.6; }}
                .popup-manager-close-bar {{ background: #f8f9fa; padding: 10px 15px; border-top: 1px solid #eee; display: flex; justify-content: space-between; align-items: center; }}
                .popup-manager-hide-label {{ font-size: 13px; color: #666; display: flex; align-items: center; gap: 5px; }}
                .popup-close-btn {{ padding: 6px 16px; border: 1px solid #ccc; background: #fff; border-radius: 4px; font-size: 13px; }}
            </style>
        </head>
        <body>
            <div class=\"overlay\">
                <div class=\"popup-manager-popup\">
                    <div class=\"popup-manager-content\">{popup_content}</div>
                    <div class=\"popup-manager-close-bar\">
                        <label class=\"popup-manager-hide-label\"><input type=\"checkbox\" /> {payload.get('popup_cookie_days')}일 동안 보지 않기</label>
                        <button type=\"button\" class=\"popup-close-btn\">닫기</button>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.html', mode='w', encoding='utf-8') as f:
                f.write(html_content)
                temp_path = f.name
            self.open_url_in_browser(f'file://{temp_path}')
        except Exception as e:
            messagebox.showerror("미리보기 오류", f"팝업 미리보기 생성 중 오류가 발생했습니다:\n{str(e)}")

    def parse_json_response(self, response):
        try:
            return response.json()
        except Exception as e:
            text = ""
            try:
                text = (response.content or b"").decode('utf-8-sig', errors='replace').strip()
            except Exception:
                text = (response.text or "").strip()

            if text:
                try:
                    return json.loads(text)
                except Exception:
                    pass

                start = text.find('{')
                end = text.rfind('}')
                if start != -1 and end != -1 and end > start:
                    snippet_json = text[start:end + 1]
                    try:
                        return json.loads(snippet_json)
                    except Exception:
                        pass

            preview = text[:300].replace('\n', ' ') if text else '응답 본문 없음'
            raise ValueError(f"JSON 파싱 실패: {str(e)} | 응답 미리보기: {preview}")

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

        if profile_data.get('create_popup', 'N') == 'Y':
            self.create_popup_check.select()
        else:
            self.create_popup_check.deselect()

        popup_scope = profile_data.get('popup_scope', '메인 인덱스')
        _scope_map = {
            '현재 게시판 페이지': '현재 게시판',
            '현재 게시판': '현재 게시판',
            '전체 페이지': '전체 페이지',
            '메인 인덱스 페이지': '메인 인덱스',
            '메인 인덱스': '메인 인덱스',
        }
        self.popup_scope_combo.set(_scope_map.get(popup_scope, '메인 인덱스'))

        self.popup_start_entry.delete(0, tk.END)
        self.popup_start_entry.insert(0, profile_data.get('popup_start_date', ''))
        self.popup_end_entry.delete(0, tk.END)
        self.popup_end_entry.insert(0, profile_data.get('popup_end_date', ''))
        self.popup_cookie_days_entry.delete(0, tk.END)
        self.popup_cookie_days_entry.insert(0, str(profile_data.get('popup_cookie_days', '1')))
        self.popup_width_entry.delete(0, tk.END)
        self.popup_width_entry.insert(0, str(profile_data.get('popup_width', "400")))
        
        self.popup_ai_entry.set(profile_data.get('popup_ai_instruction', '간략하고 명확한 3줄 요약 (기본)'))

        self.set_popup_content_text('')

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
                'create_popup': 'N',
                'popup_scope': self.popup_scope_combo.get().strip(),
                'popup_start_date': '',
                'popup_end_date': '',
                'popup_cookie_days': self.popup_cookie_days_entry.get().strip(),
                'popup_width': self.popup_width_entry.get().strip(),
                'popup_ai_instruction': self.popup_ai_entry.get().strip(),

                'popup_content': self.get_popup_content_text(),
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
            'create_popup': 'N',
            'popup_scope': self.popup_scope_combo.get().strip(),
            'popup_start_date': '',
            'popup_end_date': '',
            'popup_cookie_days': self.popup_cookie_days_entry.get().strip(),
            'popup_width': self.popup_width_entry.get().strip(),
            'popup_ai_instruction': self.popup_ai_entry.get().strip(),

            'popup_content': self.get_popup_content_text(),
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

        # Plain Text 여부 판단: 스타일 선택이 Plain Text 이거나 HTML 태그가 없는 경우
        selected_style = getattr(self, 'style_combo', None)
        selected_style = selected_style.get() if selected_style else ""
        is_plain = (selected_style == '일반 텍스트 (Plain Text)') or ('<' not in content)

        if is_plain:
            import html as _html_mod
            body_html = (
                '<pre style="white-space:pre-wrap; word-wrap:break-word; '
                'font-family:\'Pretendard\',\'Noto Sans KR\',sans-serif; '
                'font-size:15px; line-height:1.9; color:#333;">'
                + _html_mod.escape(content)
                + '</pre>'
            )
        else:
            body_html = content

        html_content = f"""
        <!DOCTYPE html>
        <html lang="ko">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>PostMoon Preview</title>
            <style>body {{ font-family: 'Pretendard','Noto Sans KR','Arial',sans-serif; padding: 20px; line-height: 1.6; }}</style>
        </head>
        <body>{body_html}</body>
        </html>
        """
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.html', mode='w', encoding='utf-8') as f:
                f.write(html_content)
                temp_path = f.name
            self.open_url_in_browser(f'file://{temp_path}')
                
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
            err_str = str(e)
            if "429" in err_str or "quota" in err_str.lower() or "RESOURCE_EXHAUSTED" in err_str:
                msg = ("Gemini API 요청 한도(Quota) 초과\n\n"
                       "무료 플랜의 분당 요청 횟수 제한에 도달했습니다.\n"
                       "잠시 후(10~30초) 다시 시도해주세요.\n\n"
                       "반복 발생 시: https://ai.google.dev/gemini-api/docs/rate-limits")
            else:
                msg = err_str
            self.root.after(0, lambda m=msg: messagebox.showerror("AI 분석 오류", m))
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
            err_str = str(e)
            if "429" in err_str or "quota" in err_str.lower() or "RESOURCE_EXHAUSTED" in err_str:
                msg = ("Gemini API 요청 한도(Quota) 초과\n\n"
                       "잠시 후(10~30초) 다시 시도해주세요.")
            else:
                msg = err_str
            self.root.after(0, lambda m=msg: messagebox.showerror("AI 수정 오류", m))
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
        self.set_popup_content_text(self.build_simplified_popup_content(title, body))
        self.tabview.set("📝  게시글 편집")  # AI 완료 후 게시글 탭으로 자동 전환

    def fetch_rhymix_menus_thread(self):
        threading.Thread(target=self.fetch_rhymix_menus, daemon=True).start()
        
    def fetch_rhymix_menus(self):
        api_url = self.api_url_entry.get().strip()
        api_key = self.api_key_entry.get().strip()
        desired_mid = self.get_pure_mid()
        
        if not api_url or not api_key:
            return messagebox.showwarning("입력 필요", "Rhymix URL과 API Key를 먼저 입력해주세요.")
            
        self.fetch_mid_btn.configure(text="⏳ 불러오는 중...", state="disabled")
        headers = {"Authorization": f"Bearer {api_key}", "X-Api-Key": api_key}
        data = {"action": "get_menu_list", "writable_only": 1}
        
        try:
            response = requests.post(api_url, headers=headers, data=data)
            if response.status_code == 200:
                result = self.parse_json_response(response)
                index_page = result.get('index_page', {}) if isinstance(result, dict) else {}
                try:
                    self.popup_index_module_srl = int(index_page.get('module_srl', 0) or 0)
                except Exception:
                    self.popup_index_module_srl = 0
                self.popup_index_mid = str(index_page.get('mid', '') or '').strip()

                scope_values = ["현재 게시판 페이지", "전체 페이지"]
                if self.popup_index_module_srl > 0:
                    scope_values.append(f"메인 인덱스 페이지 ({self.popup_index_mid or 'index'})")
                else:
                    scope_values.append("메인 인덱스 페이지")
                current_scope = self.popup_scope_combo.get().strip()
                self.root.after(0, lambda: self.popup_scope_combo.configure(values=scope_values))
                self.root.after(0, lambda: self.popup_scope_combo.set(current_scope if current_scope in scope_values else scope_values[0]))

                if result.get('error') == 0 and 'menu_list' in result:
                    menu_items = result['menu_list']
                    combo_values = []
                    preset = self._get_domain_preset()
                    if bool(self.preset_switch.get()) and preset and preset.get('include_mids'):
                        include = set(preset['include_mids'])
                        if desired_mid:
                            include.add(desired_mid)
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

                    selected_menu = combo_values[0]
                    if desired_mid:
                        for menu_text in combo_values:
                            m = re.search(r'\(([^)]+)\)$', menu_text)
                            menu_mid = m.group(1).strip() if m else menu_text.strip()
                            if menu_mid == desired_mid:
                                selected_menu = menu_text
                                break
                        
                    self.root.after(0, lambda: self.mid_entry.configure(values=combo_values))
                    self.root.after(0, lambda: self.mid_entry.set(selected_menu))
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
        try:
            self.save_config()
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
        current_mid = self.get_pure_mid()
        preset = self._get_domain_preset()
        include = preset.get('include_mids')
        if not include:
            return
        include_set = set(include)
        if current_mid:
            include_set.add(current_mid)
        filtered = []
        for v in values:
            m = re.search(r'\(([^)]+)\)$', v)
            mid = m.group(1) if m else v
            if mid in include_set:
                filtered.append(v)
        if filtered:
            selected = filtered[0]
            if current_mid:
                for v in filtered:
                    m = re.search(r'\(([^)]+)\)$', v)
                    mid = m.group(1) if m else v
                    if mid == current_mid:
                        selected = v
                        break
            self.root.after(0, lambda: self.mid_entry.configure(values=filtered))
            self.root.after(0, lambda: self.mid_entry.set(selected))

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
                result = self.parse_json_response(response)
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
        if self.create_popup_var.get() == "Y":
            popup_payload = self.collect_popup_payload(title, content)
            if not popup_payload:
                return
            data.update(popup_payload)
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
            
            result = self.parse_json_response(response)
            if result.get('success') or result.get('error') == 0:
                popup_requested_local = self.create_popup_var.get() == "Y"
                popup_requested_server = bool(result.get('popup_requested'))
                popup_created = bool(result.get('popup_created'))
                popup_error = result.get('popup_error', '')

                if popup_requested_local and not popup_requested_server:
                    messagebox.showwarning("부분 성공", "게시글은 전송되었지만 서버에서 팝업 요청을 인식하지 못했습니다.\nsecure_api.php가 최신 버전인지 확인해주세요.")
                elif popup_requested_server and popup_created:
                    messagebox.showinfo("성공", "게시글 전송 및 팝업 등록이 완료되었습니다.")
                elif popup_requested_server and not popup_created:
                    if popup_error:
                        messagebox.showwarning("부분 성공", f"게시글은 전송되었지만 팝업 등록에 실패했습니다.\n\n사유: {popup_error}")
                    else:
                        messagebox.showwarning("부분 성공", "게시글은 전송되었지만 팝업 등록이 되지 않았습니다.")
                else:
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
            
            self.set_popup_content_text("")
    # [데이터_처리_기능_종료]

if __name__ == "__main__":
    app_root = ctk.CTk()
    app = PostMoonApp(app_root)
    app_root.mainloop()
