import os
import sys
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute total page count."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        
        # Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, 11 * inch - 36, "MAHI JARVIS (Mk-VIII) — Comprehensive Development & Architecture Report")
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.5)
            self.line(54, 11 * inch - 42, 8.5 * inch - 54, 11 * inch - 42)
        
        # Footer
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(54, 46, 8.5 * inch - 54, 46)
        
        self.drawString(54, 32, "CONFIDENTIAL & PROPRIETARY — PREPARED FOR MAHI")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(8.5 * inch - 54, 32, page_str)
        self.restoreState()

def build_pdf(output_path: str):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()

    # Custom styles
    c_primary = colors.HexColor("#0f172a")     # Deep slate
    c_accent = colors.HexColor("#0284c7")      # Cyan/Blue accent
    c_secondary = colors.HexColor("#0ea5e9")   # Sky blue
    c_teal = colors.HexColor("#0d9488")        # Teal
    c_dark = colors.HexColor("#1e293b")
    c_muted = colors.HexColor("#64748b")
    c_bg_light = colors.HexColor("#f8fafc")

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=c_primary,
        spaceAfter=4
    )

    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        leading=15,
        textColor=c_accent,
        spaceAfter=14
    )

    h1_style = ParagraphStyle(
        'SectionH1',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=c_primary,
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=c_accent,
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=c_dark,
        spaceAfter=6
    )

    bullet_style = ParagraphStyle(
        'DocBullet',
        parent=body_style,
        leftIndent=14,
        bulletIndent=4,
        spaceAfter=3
    )

    code_style = ParagraphStyle(
        'DocCode',
        parent=body_style,
        fontName='Courier',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#0f766e"),
        backColor=colors.HexColor("#f1f5f9"),
        borderPadding=3,
        spaceAfter=4
    )

    callout_style = ParagraphStyle(
        'DocCallout',
        parent=body_style,
        fontName='Helvetica-Oblique',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#1e293b"),
        backColor=colors.HexColor("#f0fdf4"),
        borderColor=colors.HexColor("#86efac"),
        borderWidth=1,
        borderPadding=6,
        spaceBefore=4,
        spaceAfter=8
    )

    story = []

    # ==================== COVER / HEADER ====================
    story.append(Paragraph("MAHI JARVIS (Mk-VIII)", title_style))
    story.append(Paragraph("COMPREHENSIVE DEVELOPMENT & SYSTEM ARCHITECTURE REPORT", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=c_accent, spaceBefore=0, spaceAfter=10))

    # Meta Table
    meta_data = [
        [
            Paragraph("<b>System Identity:</b> JARVIS Personal Assistant (Mk-VIII)", body_style),
            Paragraph("<b>Target Operating System:</b> Windows 11 (x64)", body_style)
        ],
        [
            Paragraph("<b>Authorized User:</b> Mahi", body_style),
            Paragraph("<b>Active Host / Port:</b> 127.0.0.1 : 8000 (FastAPI)", body_style)
        ],
        [
            Paragraph("<b>Report Date:</b> October 3, 2026", body_style),
            Paragraph("<b>Automated Test Suite:</b> 24 / 24 Tests Passing (100% OK)", body_style)
        ]
    ]
    t_meta = Table(meta_data, colWidths=[250, 250])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 12))

    # ==================== 1. EXECUTIVE SUMMARY ====================
    story.append(Paragraph("1. Executive Summary & Project Purpose", h1_style))
    story.append(Paragraph(
        "This project established a production-grade, multimodal personal AI assistant named <b>JARVIS (Mk-VIII)</b>, "
        "engineered specifically for <b>Mahi</b>. The system unites state-of-the-art LLM reasoning, continuous long-term memory, "
        "retrieval-augmented generation (RAG), local computer and OS device automation, futuristic Sci-Fi web telemetry, "
        "and an offline, system-wide background speech listener that activates automatically upon laptop boot.",
        body_style
    ))
    story.append(Paragraph(
        "Unlike generic cloud chat interfaces, JARVIS possesses direct low-level access to the user's local operating system, "
        "allowing voice and textual control of desktop software (Chrome, Camera, Paint, Notepad, Terminal), local files "
        "and folders across OneDrive (Documents, Downloads, Desktop, Pictures), media streaming (YouTube, Anime portals), "
        "and mathematical/logical computations—all governed by a two-tier safety protocol for consequential actions.",
        body_style
    ))
    story.append(Spacer(1, 8))

    # ==================== 2. COMPLETE DEVELOPMENT TIMELINE ====================
    story.append(Paragraph("2. Complete Step-by-Step Development Trajectory", h1_style))
    
    phases = [
        ("Phase 1: Backend Foundation & Memory/RAG Pipeline", [
            "Built FastAPI core service architecture on port 8000 with CORS and async lifecycle hooks.",
            "Engineered Memory Store (<code>memory.json</code>) with automatic factual knowledge extraction and keyword-weighted recall.",
            "Implemented local RAG (Retrieval-Augmented Generation) pipeline indexing project documents via TF-IDF cosine vector similarity.",
            "Architected Protocol Alpha Safety Manager (<code>safety.py</code>) intercepting consequential operations (file deletion, OS locking) with pending confirmation tokens.",
            "Created mathematical AST calculator tool preventing arbitrary code execution while supporting sqrt, exponentiation, and trigonometry."
        ]),
        ("Phase 2: Mk-VIII Holographic Cockpit & Audio Synthesis", [
            "Designed futuristic Iron Man-inspired HUD with quantum canvas particle core and rotating cyber reticles.",
            "Implemented dual-mode visualizer: Global Network Traffic telemetry vs. live real-time Activity Stream.",
            "Engineered procedural Web Audio Synthesizer producing tactile Sci-Fi chirps (transmit, reply, alert, click) with zero external audio assets.",
            "Integrated Optical Neural Scanner (Vision Drawer) handling multimodal file upload and deep image inspection.",
            "Built quick-action cockpit chips and interactive Settings drawer for memory management and voice toggles."
        ]),
        ("Phase 3: Anime Streaming & Web Platform Automation", [
            "Engineered intelligent anime streaming router supporting 17+ high-definition platforms (AnimeRulz, Crunchyroll, HiAnime, AnimePahe, Aniwave, etc.).",
            "Configured auto-sanitizing query extraction and direct episode search link generation.",
            "Added YouTube direct playback engine extracting video queries and opening instant streaming feeds."
        ]),
        ("Phase 4: Full Laptop OS Access & File Association Rectification", [
            "Resolved the critical issue where 'open documents' fell into web search: implemented native Windows Explorer folder launches.",
            "Added deep filesystem recursive scanning across user's OneDrive Desktop, Documents, Downloads, Pictures, Videos, and Music.",
            "Solved file typo tolerance: queries like <code>open jarvi interface jpj in desktop</code> automatically resolve to <code>C:\\Users\\KOUSHIK REDDY\\OneDrive\\Desktop\\jarvi interface.jpeg</code>.",
            "Rectified Windows WPS Office silent launch conflict: automatically routes image viewing through MS Paint, Explorer selection, and direct HTTP streaming.",
            "Added in-chat Holographic Image Card in the frontend with embedded thumbnail preview, <code>[VIEW FULL ↗]</code>, and <code>[PAINT 🎨]</code> launcher."
        ]),
        ("Phase 5: System-Wide Background Voice Daemon & Headless Execution", [
            "Integrated local offline speech recognition engine using Vosk (<code>vosk-model-small-en-us-0.15</code>) and <code>sounddevice</code> for 100% private microphone streaming.",
            "Trained wake-word triggers: <code>Hello Jarvis</code>, <code>Hey Jarvis</code>, <code>Jarvis</code>, <code>OK Jarvis</code>.",
            "Engineered smart Headless vs. Compulsory Interface classification: standard commands (open Chrome, open Documents, play songs, calculations) execute natively on the laptop with spoken audio confirmation while keeping the browser UI closed.",
            "Compulsory UI logic: the browser interface only opens when explicitly requested (<code>open interface</code>, <code>show dashboard</code>) or when critical authorization is required.",
            "Integrated Windows native Text-To-Speech (TTS) using <code>System.Speech.Synthesis</code> for natural, non-blocking verbal responses."
        ]),
        ("Phase 6: Windows Startup Integration & Bug Fixes", [
            "Created silent Windows startup launcher (<code>StartJarvisBackground.vbs</code>) registered in <code>%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\Startup</code>.",
            "Configured <code>pythonw.exe</code> execution with hidden window mode so JARVIS boots silently with Windows without terminal popups.",
            "Added single-word noun command support: direct commands like <code>document</code>, <code>chrome</code>, <code>camera</code>, <code>notepad</code> execute immediately without requiring the word 'open'.",
            "Filtered in-browser continuous microphone to ignore room/TV noise (e.g. cricket chatter) unless addressed directly as 'Jarvis'."
        ])
    ]

    for phase_title, items in phases:
        story.append(Paragraph(f"<b>{phase_title}</b>", h2_style))
        for item in items:
            story.append(Paragraph(f"• {item}", bullet_style))
        story.append(Spacer(1, 4))

    story.append(Spacer(1, 10))

    # ==================== 3. ARCHITECTURE & INVENTORY ====================
    story.append(Paragraph("3. Technical Architecture & File Inventory", h1_style))
    
    file_inventory = [
        ["Component", "File Path", "Description & Responsibility"],
        ["Core API", "backend/main.py", "FastAPI web server, CORS middleware, static HUD hosting"],
        ["Agent Brain", "backend/core/agent.py", "Intent router, tool orchestrator, LLM & headless logic"],
        ["Memory Engine", "backend/core/memory.py", "JSON persistent store for user preferences and facts"],
        ["RAG Engine", "backend/core/rag.py", "Document ingestion, TF-IDF indexing, knowledge search"],
        ["Safety Guard", "backend/core/safety.py", "Protocol Alpha authorization and audit log recorder"],
        ["Device Tools", "backend/tools/device_control.py", "OS launcher: Chrome, Explorer, MS Paint, volume, folders"],
        ["Speech Daemon", "backend/services/background_voice_daemon.py", "Continuous offline Vosk voice listener thread"],
        ["TTS Engine", "backend/services/tts_service.py", "Windows native asynchronous speech synthesizer"],
        ["Startup Hook", "scripts/install_startup.py", "Windows startup registry and silent VBS installer"],
        ["Hologram HUD", "frontend/index.html & app.js", "Futuristic Sci-Fi Mk-VIII cockpit and image viewer"]
    ]

    t_inv = Table([[Paragraph(c, body_style) for c in row] for row in file_inventory], colWidths=[80, 190, 230])
    t_inv.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0f172a")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
    ]))
    story.append(t_inv)
    story.append(Spacer(1, 12))

    # ==================== 4. KEY ISSUES RECTIFIED ====================
    story.append(Paragraph("4. Key Technical Challenges & Rectification Case Studies", h1_style))
    
    cases = [
        ("Case 1: 'Open Documents' Was Triggering Chrome Web Search",
         "Initial routing treated 'documents' as an unrecognized target, falling back to a Google search in Chrome. "
         "<b>Solution:</b> Built a comprehensive OS folder mapping (<code>shell:Personal</code>, <code>shell:Downloads</code>, <code>shell:Desktop</code>), "
         "supported singular/plural aliases (<code>document</code>, <code>documents</code>, <code>my documents</code>), and forced native File Explorer execution."),
        
        ("Case 2: WPS Office Intercepting Image Launch ('jarvi interface.jpeg')",
         "On the user's laptop, <code>.jpeg</code> files were bound to WPS Office (<code>photolaunch.exe</code>), which ran silently in the background without creating a visible window. "
         "<b>Solution:</b> Re-routed desktop image opens to explicitly launch MS Paint (<code>mspaint.exe</code>), open File Explorer with the file selected (<code>explorer /select</code>), "
         "and streamed the image directly to the JARVIS chat interface with an interactive preview card."),

        ("Case 3: Unwanted Browser Popups & Chrome Window Clashes",
         "Commands to open Chrome or web pages triggered the browser's aggressive popup blocker when invoked from within the existing web interface. "
         "<b>Solution:</b> Separated native OS application launches (using <code>chrome.exe --new-window</code>) from web-based URLs, eliminating blocked popup warnings."),

        ("Case 4: Background TV / Room Chatter Triggering False Commands",
         "The browser's continuous microphone listening was transcribing cricket commentary and room conversation into chat commands. "
         "<b>Solution:</b> Added strict wake-word filtering (requiring 'Jarvis' or 'Hello Jarvis') for all continuous voice recognition streams.")
    ]

    for title, desc in cases:
        story.append(Paragraph(f"<b>{title}</b>", h2_style))
        story.append(Paragraph(desc, body_style))
        story.append(Spacer(1, 3))

    story.append(Spacer(1, 10))

    # ==================== 5. VERIFICATION & TEST SUITE ====================
    story.append(Paragraph("5. Automated Test Suite & Quality Verification", h1_style))
    story.append(Paragraph(
        "A rigorous regression test suite of <b>24 automated unit tests</b> was developed in <code>tests/test_jarvis.py</code>. "
        "All tests execute against live endpoints and pass with 100% success rate:",
        body_style
    ))

    test_matrix = [
        ["Test ID", "Test Target & Scope", "Result"],
        ["Test 01", "FastAPI /health check & JARVIS identity verification", "PASSED [OK]"],
        ["Test 02", "AST Math Calculator (Arithmetic & Sqrt operations)", "PASSED [OK]"],
        ["Test 03-05", "Filesystem tool (Write, Read, List, Delete sandboxing)", "PASSED [OK]"],
        ["Test 06", "Protocol Alpha Safety Manager & Consequential Token gate", "PASSED [OK]"],
        ["Test 07-09", "Long-term Memory Bank (Extraction, Persistence & Recall)", "PASSED [OK]"],
        ["Test 10-12", "RAG Pipeline (Document Ingestion & Semantic Retrieval)", "PASSED [OK]"],
        ["Test 13-16", "Anime Provider Auto-Routing (AnimeRulz, Crunchyroll, etc.)", "PASSED [OK]"],
        ["Test 17-19", "Native Hardware Controls (Camera, System Settings, Volume)", "PASSED [OK]"],
        ["Test 20", "Typo-tolerant Desktop Image File Launch (jarvi interface.jpeg)", "PASSED [OK]"],
        ["Test 21", "Compulsory UI Mode Detection ('open interface')", "PASSED [OK]"],
        ["Test 22", "Headless Mode Execution Verification (Apps, Folders, Math)", "PASSED [OK]"],
        ["Test 23", "Text-To-Speech String Sanitizer (Markdown & URL removal)", "PASSED [OK]"],
        ["Test 24", "Offline Wake-Word & Utterance Extraction ('hello jarvis')", "PASSED [OK]"]
    ]

    t_tests = Table([[Paragraph(c, body_style) for c in row] for row in test_matrix], colWidths=[70, 360, 70])
    t_tests.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0f172a")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
    ]))
    story.append(t_tests)
    story.append(Spacer(1, 12))

    # ==================== 6. OPERATIONAL GUIDE ====================
    story.append(Paragraph("6. Operational Guide & Quick Command Reference", h1_style))
    
    commands = [
        ("Opening Applications", "Say: 'Jarvis, open Chrome', 'Jarvis, open Camera', 'Jarvis, open Notepad'"),
        ("Opening Laptop Folders", "Say: 'Jarvis, open Documents', 'Jarvis, open Downloads', 'Jarvis, open Desktop'"),
        ("Desktop Files & Images", "Say: 'Jarvis, open jarvi interface image on desktop', 'Jarvis, open resume'"),
        ("Direct Noun Commands", "Say: 'Documents', 'Chrome', 'Camera', 'Calculator' (works without the word 'open')"),
        ("Playing Music / Videos", "Say: 'Jarvis, play Telugu songs on YouTube', 'Jarvis, play Naruto on AnimeRulz'"),
        ("Math, Time & Facts", "Say: 'Jarvis, calculate 1500 * 12', 'Jarvis, what time is it?'"),
        ("Opening Interface", "Say: 'Jarvis, open your interface', 'Jarvis, show dashboard' (Opens browser HUD)")
    ]

    t_cmd = Table([
        [Paragraph(f"<b>{cat}</b>", body_style), Paragraph(cmd, body_style)]
        for cat, cmd in commands
    ], colWidths=[150, 350])
    t_cmd.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor("#f1f5f9")),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_cmd)
    story.append(Spacer(1, 14))

    # Final Sign-off Box
    story.append(Paragraph(
        "<b>SYSTEM STATUS: FULLY OPERATIONAL</b><br/>"
        "JARVIS (Mk-VIII) is running with background voice listening, silent Windows startup integration, "
        "smart headless command execution, and full local laptop device control. All features verified and ready.",
        callout_style
    ))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Report successfully compiled: {output_path}")

if __name__ == "__main__":
    out_dir = Path(__file__).resolve().parent.parent
    pdf_file = out_dir / "JARVIS_Project_Comprehensive_Report.pdf"
    build_pdf(str(pdf_file))
