import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import requests
import os
import json
import threading
import tempfile
import webbrowser
from urllib.parse import urlparse

# Try to import Google Generative AI library
try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

class PostMoonApp:
    def __init__(self, root):
        self.root = root
        self.VERSION = "v1.5.1" # Updated for Folder Upload Support & Bug Fixes
        self.root.title(f"PostMoon - AI Powered Rhymix Uploader {self.VERSION}")
        self.root.geometry("1200x900") # Increased size for better split view

        self.chat_session = None # To store AI chat history

        # --- Footer ---
        footer_frame = tk.Frame(root, bg="#f0f0f0", padx=10, pady=5)
        footer_frame.pack(side="bottom", fill="x")
        
        tk.Label(footer_frame, text=f"PostMoon {self.VERSION} | 제작자 : mOOnster", fg="gray", font=("Arial", 9), bg="#f0f0f0").pack(side="left")

        # --- Main Layout (Split View) ---
        # Use PanedWindow for adjustable split
        self.paned_window = tk.PanedWindow(root, orient=tk.HORIZONTAL, sashwidth=5, bg="#dcdcdc")
        self.paned_window.pack(fill="both", expand=True, padx=5, pady=5)

        # --- Left Panel: Raw Input & AI Control ---
        self.left_frame = tk.Frame(self.paned_window, padx=10, pady=10, bg="#f0f0f0")
        self.paned_window.add(self.left_frame, minsize=400)

        # Left Header
        tk.Label(self.left_frame, text="📝 원문 입력 (Raw Input)", font=("Arial", 14, "bold"), bg="#f0f0f0").pack(side="top", anchor="w", pady=(0, 10))

        # AI Control Frame (Style Selection + Button)
        ai_control_frame = tk.Frame(self.left_frame, bg="#f0f0f0")
        ai_control_frame.pack(side="bottom", fill="x", pady=(10, 10))

        # Style Selection Label
        tk.Label(ai_control_frame, text="출력 스타일 선택 (Output Style):", font=("Arial", 10, "bold"), bg="#f0f0f0").pack(anchor="w")
        
        # Style Combobox
        self.style_var = tk.StringVar()
        self.style_combo = ttk.Combobox(ai_control_frame, textvariable=self.style_var, state="readonly", font=("Arial", 10))
        self.style_combo['values'] = ('일반 텍스트 (Plain Text)', 'HTML 보도자료 스타일', 'HTML 국가대표 시범단 공지 스타일', 'HTML 세계줄넘기위원회 공지 스타일')
        self.style_combo.current(0) # Default selection
        self.style_combo.pack(fill="x", pady=(5, 10))

        # AI Action Button
        self.ai_btn = tk.Button(ai_control_frame, text="✨ AI 분석 및 정리 (Gemini)", 
                                command=self.process_with_ai_thread, 
                                bg="#673ab7", fg="white", font=("Arial", 12, "bold"), height=2)
        self.ai_btn.pack(fill="x")

        # Raw Text Input (Fills remaining space)
        self.raw_text_entry = scrolledtext.ScrolledText(self.left_frame, font=("Arial", 10))
        self.raw_text_entry.pack(side="top", fill="both", expand=True)
        
        # --- Right Panel: Result & Config ---
        self.right_frame = tk.Frame(self.paned_window, padx=10, pady=10)
        self.paned_window.add(self.right_frame, minsize=550)

        # Right Header
        tk.Label(self.right_frame, text="🚀 결과 확인 및 전송 (Result)", font=("Arial", 14, "bold")).pack(anchor="w", pady=(0, 10))

        # --- Settings Summary & Toggle ---
        settings_summary_frame = tk.Frame(self.right_frame)
        settings_summary_frame.pack(fill="x", pady=(0, 5))
        
        self.toggle_settings_btn = tk.Button(settings_summary_frame, text="⚙️ 설정 열기", command=self.toggle_settings, width=12)
        self.toggle_settings_btn.pack(side="left")
        
        self.current_target_label = tk.Label(settings_summary_frame, text="현재 타겟: -", fg="gray", font=("Arial", 9))
        self.current_target_label.pack(side="left", padx=10)

        # --- Configuration Wrapper (Collapsible) ---
        self.config_wrapper = tk.Frame(self.right_frame)
        # Note: We do NOT pack it here, effectively hiding it on startup.
        
        config_frame = tk.LabelFrame(self.config_wrapper, text="설정 (Settings)", padx=10, pady=5)
        config_frame.pack(fill="x", pady=(0, 5))

        # --- Profile Management ---
        profile_frame = tk.Frame(config_frame)
        profile_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        tk.Label(profile_frame, text="프로필 선택:", font=("Arial", 9, "bold")).pack(side="left")
        
        self.profile_var = tk.StringVar()
        self.profile_combo = ttk.Combobox(profile_frame, textvariable=self.profile_var, state="readonly", width=20)
        self.profile_combo.pack(side="left", padx=5)
        self.profile_combo.bind("<<ComboboxSelected>>", self.on_profile_change)
        
        tk.Button(profile_frame, text="➕ 추가", command=self.add_profile, width=6, bg="#e0e0e0").pack(side="left", padx=2)
        tk.Button(profile_frame, text="🗑️ 삭제", command=self.delete_profile, width=6, bg="#ffcdd2").pack(side="left", padx=2)

        # Config Grid
        tk.Label(config_frame, text="Rhymix URL:").grid(row=1, column=0, sticky="w", pady=2)
        self.api_url_entry = tk.Entry(config_frame)
        self.api_url_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=2)
        
        tk.Label(config_frame, text="Rhymix API Key:").grid(row=2, column=0, sticky="w", pady=2)
        self.api_key_entry = tk.Entry(config_frame, show="*") # Masked for security
        self.api_key_entry.grid(row=2, column=1, sticky="ew", padx=5, pady=2)

        tk.Label(config_frame, text="게시판 ID (mid):").grid(row=3, column=0, sticky="w", pady=2)
        self.mid_entry = tk.Entry(config_frame)
        self.mid_entry.grid(row=3, column=1, sticky="ew", padx=5, pady=2)

        tk.Label(config_frame, text="Gemini API Key:").grid(row=4, column=0, sticky="w", pady=2)
        self.gemini_key_entry = tk.Entry(config_frame, show="*") # Masked for security
        self.gemini_key_entry.grid(row=4, column=1, sticky="ew", padx=5, pady=2)

        config_frame.columnconfigure(1, weight=1)

        # Save config button
        self.save_cfg_btn = tk.Button(self.config_wrapper, text="💾 현재 프로필 저장", command=self.save_config_manual, bg="#28a745", fg="white", font=("Arial", 10, "bold"))
        self.save_cfg_btn.pack(fill="x", pady=(0, 10))

        # --- Post Content Section ---
        self.content_frame = tk.LabelFrame(self.right_frame, text="게시글 내용", padx=10, pady=5)
        self.content_frame.pack(fill="both", expand=True, pady=(0, 10))

        tk.Label(self.content_frame, text="제목:").pack(anchor="w")
        self.title_entry = tk.Entry(self.content_frame, font=("Arial", 11))
        self.title_entry.pack(fill="x", pady=(0, 5))

        tk.Label(self.content_frame, text="본문:").pack(anchor="w")
        self.content_text = scrolledtext.ScrolledText(self.content_frame, font=("Arial", 10), height=15)
        self.content_text.pack(fill="both", expand=True, pady=(0, 5))

        # --- HTML Preview Button ---
        preview_btn = tk.Button(self.content_frame, text="🌐 웹 브라우저에서 미리보기", command=self.preview_html, 
                                bg="#17a2b8", fg="white", font=("Arial", 9, "bold"))
        preview_btn.pack(anchor="e", pady=(0, 5))

        # --- Refinement Section (New Feature) ---
        refine_frame = tk.Frame(self.content_frame)
        refine_frame.pack(fill="x", pady=(5, 0))

        tk.Label(refine_frame, text="AI 추가 수정 지시 (Refinement):", font=("Arial", 9, "bold")).pack(anchor="w")
        
        self.refine_entry = tk.Entry(refine_frame, font=("Arial", 10))
        self.refine_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.refine_entry.bind("<Return>", lambda event: self.refine_with_ai_thread())

        self.refine_btn = tk.Button(refine_frame, text="🔄 이대로 다시 수정 (Refine)", 
                                    command=self.refine_with_ai_thread,
                                    bg="#ff9800", fg="white", font=("Arial", 9, "bold"))
        self.refine_btn.pack(side="right")

        # --- File Upload Section ---
        file_frame = tk.Frame(self.right_frame)
        file_frame.pack(fill="x", pady=(0, 10))

        self.selected_files = []
        
        self.file_btn = tk.Button(file_frame, text="📎 첨부파일 선택", command=self.select_files)
        self.file_btn.pack(side="left")
        
        self.file_label = tk.Label(file_frame, text="선택된 파일 없음", fg="gray")
        self.file_label.pack(side="left", padx=10)

        # --- Update Check Button ---
        update_btn = tk.Button(file_frame, text="🔄 업데이트 확인", command=self.check_for_updates_thread, 
                               bg="#20c997", fg="white", font=("Arial", 9, "bold"))
        update_btn.pack(side="right")

        # --- Action Section ---
        self.send_btn = tk.Button(self.right_frame, text="📤 게시글 Rhymix로 전송", command=self.upload_to_rhymix_thread, 
                                  bg="#007bff", fg="white", font=("Arial", 12, "bold"), height=2)
        self.send_btn.pack(fill="x")

        # Load config on startup
        self.load_config()

        if not HAS_GENAI:
            messagebox.showwarning("라이브러리 누락", "Google Generative AI 라이브러리가 설치되지 않았습니다.\n기능 사용을 위해 'pip install google-generativeai'를 실행해주세요.")

    def toggle_settings(self):
        if self.config_wrapper.winfo_ismapped():
            self.config_wrapper.pack_forget()
            self.toggle_settings_btn.config(text="⚙️ 설정 열기")
        else:
            # Pack before content_frame to maintain order
            self.config_wrapper.pack(fill="x", pady=(0, 5), before=self.content_frame)
            self.toggle_settings_btn.config(text="⚙️ 설정 닫기")

    def update_summary_label(self):
        url = self.api_url_entry.get().strip()
        mid = self.mid_entry.get().strip()
        
        domain = "URL 미설정"
        if url:
            try:
                parsed = urlparse(url)
                domain = parsed.netloc if parsed.netloc else url
            except:
                domain = url
        
        if not mid:
            mid = "mid 미설정"
            
        self.current_target_label.config(text=f"현재 타겟: {domain} / {mid}")

    def load_config(self):
        self.profiles = {}
        self.current_profile = "Default"
        
        try:
            if os.path.exists('config.json'):
                with open('config.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # Migration logic for old config format
                    if 'api_url' in data and 'profiles' not in data:
                        self.profiles = {
                            "Default": {
                                'api_url': data.get('api_url', ''),
                                'api_key': data.get('api_key', ''),
                                'mid': data.get('mid', ''),
                                'gemini_api_key': data.get('gemini_api_key', '')
                            }
                        }
                        self.current_profile = "Default"
                    else:
                        self.profiles = data.get('profiles', {})
                        self.current_profile = data.get('last_used', 'Default')
                        
            # Ensure Default profile exists if empty
            if not self.profiles:
                self.profiles = {
                    "Default": {
                        'api_url': "",
                        'api_key': "",
                        'mid': "",
                        'gemini_api_key': ""
                    }
                }
                self.current_profile = "Default"

            # Update Combo
            self.update_profile_combo()
            
            # Load values
            self.load_profile_values()
            
            # Update summary label after loading
            self.update_summary_label()
            
        except Exception as e:
            print(f"Config load error: {e}")
            # Fallback
            self.profiles = {"Default": {'api_url': "", 'api_key': "", 'mid': "", 'gemini_api_key': ""}}
            self.current_profile = "Default"
            self.update_profile_combo()

    def update_profile_combo(self):
        profile_names = list(self.profiles.keys())
        self.profile_combo['values'] = profile_names
        if self.current_profile in profile_names:
            self.profile_combo.set(self.current_profile)
        elif profile_names:
            self.profile_combo.current(0)
            self.current_profile = self.profile_combo.get()

    def load_profile_values(self):
        profile_data = self.profiles.get(self.current_profile, {})
        
        self.api_url_entry.delete(0, tk.END)
        self.api_url_entry.insert(0, profile_data.get('api_url', ''))
        
        self.api_key_entry.delete(0, tk.END)
        self.api_key_entry.insert(0, profile_data.get('api_key', ''))
        
        self.mid_entry.delete(0, tk.END)
        self.mid_entry.insert(0, profile_data.get('mid', ''))
        
        self.gemini_key_entry.delete(0, tk.END)
        self.gemini_key_entry.insert(0, profile_data.get('gemini_api_key', ''))

    def on_profile_change(self, event):
        new_profile = self.profile_var.get()
        if new_profile:
            # Save current before switching? Maybe too aggressive. 
            # Let's just switch and load. User should save manually if they changed something.
            self.current_profile = new_profile
            self.load_profile_values()
            self.update_summary_label()
            self.save_config() # Persist the "last_used" selection

    def add_profile(self):
        from tkinter import simpledialog
        new_name = simpledialog.askstring("새 프로필", "새 프로필 이름을 입력하세요:")
        if new_name:
            if new_name in self.profiles:
                messagebox.showerror("오류", "이미 존재하는 프로필 이름입니다.")
                return
            
            # Inherit current values
            self.profiles[new_name] = {
                'api_url': self.api_url_entry.get().strip(),
                'api_key': self.api_key_entry.get().strip(),
                'mid': self.mid_entry.get().strip(),
                'gemini_api_key': self.gemini_key_entry.get().strip()
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
            # Switch to first available
            self.current_profile = list(self.profiles.keys())[0]
            self.update_profile_combo()
            self.load_profile_values()
            self.save_config()
            self.update_summary_label()

    def save_config(self):
        # Update current profile data from UI
        self.profiles[self.current_profile] = {
            'api_url': self.api_url_entry.get().strip(),
            'api_key': self.api_key_entry.get().strip(),
            'mid': self.mid_entry.get().strip(),
            'gemini_api_key': self.gemini_key_entry.get().strip()
        }
        
        config = {
            'profiles': self.profiles,
            'last_used': self.current_profile
        }
        
        try:
            with open('config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            
            # Update summary label after saving
            self.update_summary_label()
            
        except Exception as e:
            print(f"Config save error: {e}")

    def save_config_manual(self):
        self.save_config()
        messagebox.showinfo("저장 완료", "현재 프로필 설정이 저장되었습니다.")

    def select_files(self):
        files = filedialog.askopenfilenames()
        if files:
            self.selected_files = files
            self.file_label.config(text=f"선택된 파일: {len(files)}개")
        else:
            self.selected_files = []
            self.file_label.config(text="선택된 파일 없음")

    def preview_html(self):
        content = self.content_text.get("1.0", tk.END).strip()
        if not content:
            messagebox.showwarning("내용 없음", "미리보기할 본문 내용이 없습니다.")
            return
            
        # Wrap in basic HTML structure
        html_content = f"""
        <!DOCTYPE html>
        <html lang="ko">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>PostMoon Preview</title>
            <style>
                body {{ font-family: 'Arial', sans-serif; padding: 20px; line-height: 1.6; }}
                /* Basic styles to match the editor or common web styles */
                .notice-container {{
                    border: 2px solid #0056b3; 
                    padding: 20px; 
                    border-radius: 10px;
                }}
                .press-release {{
                    /* Add specific styles for press release if needed */
                }}
            </style>
        </head>
        <body>
            {content}
        </body>
        </html>
        """
        
        try:
            # Create a temporary file
            # delete=False is important so the browser can read it. 
            with tempfile.NamedTemporaryFile(delete=False, suffix='.html', mode='w', encoding='utf-8') as f:
                f.write(html_content)
                temp_path = f.name
                
            # Open in browser with forced paths for Chrome/Edge if possible
            # To avoid opening in VS Code or other editors
            url = f'file://{temp_path}'
            
            # Paths to check (Windows)
            chrome_path = r'C:/Program Files/Google/Chrome/Application/chrome.exe'
            edge_path = r'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'
            
            browser_opened = False
            
            try:
                if os.path.exists(chrome_path):
                    webbrowser.get(f'"{chrome_path}" %s').open(url)
                    browser_opened = True
                elif os.path.exists(edge_path):
                    webbrowser.get(f'"{edge_path}" %s').open(url)
                    browser_opened = True
            except Exception:
                # Fallback if specific browser launch fails
                pass
                
            if not browser_opened:
                webbrowser.open(url)
            
        except Exception as e:
            messagebox.showerror("미리보기 오류", f"브라우저를 여는 중 오류가 발생했습니다:\n{str(e)}")

    def process_with_ai_thread(self):
        threading.Thread(target=self.process_with_ai, daemon=True).start()

    def check_for_updates_thread(self):
        threading.Thread(target=self.check_for_updates, daemon=True).start()

    def check_for_updates(self):
        try:
            repo_owner = "mOOnster-Git"
            repo_name = "PostMoon"
            api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/latest"
            
            response = requests.get(api_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                latest_version = data.get("tag_name", "").strip()
                
                # Simple string comparison (assumes vX.Y.Z format)
                # Remove 'v' prefix for comparison if needed, but here just direct string compare
                current = self.VERSION
                
                if latest_version and latest_version != current:
                    if messagebox.askyesno("업데이트 확인", f"새로운 버전이 있습니다!\n현재 버전: {current}\n최신 버전: {latest_version}\n\n다운로드 페이지로 이동하시겠습니까?"):
                        webbrowser.open(data.get("html_url", "https://github.com/mOOnster-Git/PostMoon/releases"))
                else:
                    messagebox.showinfo("최신 버전", f"현재 최신 버전을 사용 중입니다.\n({current})")
            else:
                messagebox.showerror("오류", "버전 정보를 가져올 수 없습니다.")
        except Exception as e:
            messagebox.showerror("오류", f"업데이트 확인 중 오류 발생: {e}")

    def process_with_ai(self):
        if not HAS_GENAI:
            messagebox.showerror("오류", "google-generativeai 라이브러리가 필요합니다.\npip install google-generativeai")
            return

        gemini_key = self.gemini_key_entry.get().strip()
        raw_text = self.raw_text_entry.get("1.0", tk.END).strip()
        selected_style = self.style_var.get()

        if not gemini_key:
            messagebox.showwarning("설정 필요", "Gemini API Key를 입력해주세요.")
            return
        
        if not raw_text:
            messagebox.showwarning("입력 필요", "분석할 원문 텍스트를 입력해주세요.")
            return

        self.ai_btn.config(text="⏳ 분석 중...", state="disabled")
        
        try:
            # Configure Gemini
            genai.configure(api_key=gemini_key)
            # Use 'gemini-flash-latest' which is stable and generally available
            model = genai.GenerativeModel('gemini-flash-latest')

            # Build Prompt based on Style
            style_instruction = ""
            if selected_style == 'HTML 보도자료 스타일':
                style_instruction = """
                - Use HTML formatting for the body.
                - Wrap the entire body in <div class='press-release'>.
                - Use <h2> for subtitles or section headers.
                - Use <p> for paragraphs.
                - Make it professional and formal suitable for a press release.
                """
            elif selected_style == 'HTML 국가대표 시범단 공지 스타일':
                style_instruction = """
                - Use HTML formatting for the body.
                - Wrap the entire body in <div class='notice-container' style='border: 2px solid #0056b3; padding: 20px; border-radius: 10px;'>.
                - Use <h2 style='color: #0056b3; text-align: center;'> for the main title inside the body.
                - Use <strong> for emphasis on dates, locations, and important requirements.
                - Use <ul><li> for lists of items.
                - Tone should be authoritative yet encouraging, suitable for a national demonstration team.
                """
            elif selected_style == 'HTML 세계줄넘기위원회 공지 스타일':
                style_instruction = """
                - Use HTML formatting for the body.
                - Wrap the entire content in <div style='max-width: 800px; margin: 0 auto; padding: 20px; font-family: "Malgun Gothic", "Noto Sans KR", sans-serif; line-height: 1.8; color: #333;'>
                - For main subtitles or important sections inside the body, use <h3 style='color: #0b4a8e; font-size: 1.2em; margin-top: 25px; margin-bottom: 15px; border-bottom: 2px solid #0b4a8e; padding-bottom: 8px;'>
                - Emphasize important text (like dates, deadlines, or key terms) using <strong style='color: #d9534f;'> or standard <strong>.
                - Format lists cleanly for readability: <ul style='padding-left: 20px; list-style-type: square; margin-bottom: 15px;'>
                - MUST include this exact official signature at the very end of the body text:
                  <div style='margin-top: 40px; padding-top: 20px; text-align: center; font-weight: bold; font-size: 1.2em; color: #111; border-top: 1px solid #ddd;'>
                    <p>세계어린이줄넘기위원회 · 세계줄넘기위원회</p>
                  </div>
                """
            else: # Plain Text
                style_instruction = """
                - Clean, clutter-free text.
                - No HTML tags (unless line breaks are needed).
                - Use simple formatting like dashes (-) for lists.
                """

            prompt = f"""
            Task: Analyze the provided text and extract a core 1-line title suitable for a bulletin board, and a clean, clutter-free body text.
            
            Style Instructions:
            {style_instruction}
            
            General Instructions:
            1. The title should be concise and descriptive (1 line).
            2. The body should be well-organized, removing unnecessary filler words from the raw text.
            3. Use the following output format EXACTLY:
            
            TITLE: [Your Title Here]
            BODY:
            [Your Body Here]
            
            Raw Text:
            {raw_text}
            """

            # Start a new chat session for context retention
            self.chat_session = model.start_chat(history=[])
            response = self.chat_session.send_message(prompt)
            result_text = response.text

            self.parse_and_update_ui(result_text)
            
            # Save config to persist key
            self.save_config()

        except Exception as e:
            messagebox.showerror("AI 분석 오류", f"Gemini API 호출 중 오류가 발생했습니다:\n{str(e)}")
        finally:
            self.root.after(0, lambda: self.ai_btn.config(text="✨ AI 분석 및 정리 (Gemini)", state="normal"))

    def refine_with_ai_thread(self):
        threading.Thread(target=self.refine_with_ai, daemon=True).start()

    def refine_with_ai(self):
        if not self.chat_session:
            messagebox.showwarning("오류", "먼저 AI 분석을 실행해주세요.\n이전 대화 내역이 없습니다.")
            return

        instruction = self.refine_entry.get().strip()
        if not instruction:
            messagebox.showwarning("입력 필요", "수정할 내용을 입력해주세요.")
            return

        self.refine_btn.config(text="⏳ 수정 중...", state="disabled")
        
        # Get current style to allow switching styles during refinement
        current_style = self.style_var.get()

        try:
            refine_prompt = f"""
            User Instruction: {instruction}
            
            Current Style Setting: {current_style}
            (If the user asks to change style, or if the current style setting is different from before, adapt the output to this style.)
            
            Based on the above instruction, rewrite the Title and Body.
            
            IMPORTANT: You MUST return the result in the EXACT same format as before:
            
            TITLE: [Updated Title]
            BODY:
            [Updated Body]
            """
            
            response = self.chat_session.send_message(refine_prompt)
            result_text = response.text
            
            self.parse_and_update_ui(result_text)
            
            # Clear input after success
            self.root.after(0, lambda: self.refine_entry.delete(0, tk.END))

        except Exception as e:
            messagebox.showerror("AI 수정 오류", f"Gemini API 호출 중 오류가 발생했습니다:\n{str(e)}")
        finally:
            self.root.after(0, lambda: self.refine_btn.config(text="🔄 이대로 다시 수정 (Refine)", state="normal"))

    def parse_and_update_ui(self, result_text):
        # Parse Result
        title = ""
        body = ""
        
        lines = result_text.split('\n')
        is_body = False
        body_lines = []

        for line in lines:
            if line.startswith("TITLE:"):
                title = line.replace("TITLE:", "").strip()
            elif line.startswith("BODY:"):
                is_body = True
            elif is_body:
                body_lines.append(line)

        body = "\n".join(body_lines).strip()

        # Update UI (Must be in main thread)
        self.root.after(0, self.update_ui_result, title, body)

    def update_ui_result(self, title, body):
        self.title_entry.delete(0, tk.END)
        self.title_entry.insert(0, title)
        
        self.content_text.delete("1.0", tk.END)
        self.content_text.insert("1.0", body)
        
        # Flash effect or notification could be added here, but message box is annoying for every update

    def upload_to_rhymix_thread(self):
        threading.Thread(target=self.upload_to_rhymix, daemon=True).start()

    def upload_to_rhymix(self):
        # 1. Get Inputs
        # Remove ALL spaces from URL to prevent copy-paste errors
        api_url = self.api_url_entry.get().strip().replace(" ", "")
        api_key = self.api_key_entry.get().strip()
        mid = self.mid_entry.get().strip()
        title = self.title_entry.get().strip()
        content = self.content_text.get("1.0", tk.END).strip()
        selected_style = self.style_var.get()

        # Save config
        self.save_config()

        # 2. Validation
        if not api_url or not api_key or not mid or not title or not content:
            messagebox.showwarning("입력 오류", "모든 필드를 입력해주세요.")
            return

        # Convert newlines to HTML break tags ONLY IF Plain Text style is selected
        if 'HTML' not in selected_style:
             content = content.replace('\n', '<br />')
        else:
            # For HTML modes, usually we want to preserve the structure. 
            pass 

        # 3. Prepare Request
        headers = {
            "Authorization": f"Bearer {api_key}",
            "X-Api-Key": api_key
        }
        
        data = {
            "api_key": api_key,
            "action": "create_document",
            "mid": mid,
            "title": title,
            "content": content
        }

        files_to_send = []
        open_files = [] # To close files later

        try:
            # 4. Handle Files
            if self.selected_files:
                for file_path in self.selected_files:
                    if os.path.exists(file_path):
                        f = open(file_path, 'rb')
                        open_files.append(f)
                        # requests handles list of tuples with same key as array
                        files_to_send.append(('file[]', (os.path.basename(file_path), f, 'application/octet-stream')))
            
            # 5. Send Request
            self.root.after(0, lambda: self.send_btn.config(text="전송 중...", state="disabled"))
            
            print(f"Sending to {api_url} with mid={mid}, title={title}")
            
            response = requests.post(api_url, headers=headers, data=data, files=files_to_send)
            response.raise_for_status()
            
            result = response.json()
            
            if result.get('success') or result.get('error') == 0:
                messagebox.showinfo("성공", "게시글이 성공적으로 전송되었습니다.")
                # Clear inputs
                self.selected_files = []
                self.file_label.config(text="선택된 파일 없음")
                self.raw_text_entry.delete("1.0", tk.END)
                self.title_entry.delete(0, tk.END)
                self.content_text.delete("1.0", tk.END)
                self.refine_entry.delete(0, tk.END)
            else:
                messagebox.showerror("실패", f"전송 실패: {result.get('message', '알 수 없는 오류')}")
                
        except Exception as e:
            messagebox.showerror("오류", f"전송 중 오류 발생: {str(e)}")
        finally:
            # Clean up files
            for f in open_files:
                f.close()
            self.root.after(0, lambda: self.send_btn.config(text="📤 게시글 Rhymix로 전송", state="normal"))

if __name__ == "__main__":
    root = tk.Tk()
    app = PostMoonApp(root)
    root.mainloop()
